import base64
import binascii
import json
import re
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session, selectinload

from .accounting import create_journal_entry, list_accounts_with_balances
from .models import (
    Account,
    AccountType,
    CompanySettings,
    Contact,
    ContactType,
    Employee,
    PayrollRun,
    PayrollStatus,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    Receipt,
    ReceiptExtraction,
    ReceiptExtractionStatus,
    ReceiptLineItem,
    TransactionKind,
    TransactionStatus,
    OperationalTransaction,
    VendorQualificationStatus,
)
from .schemas import (
    AccountRead,
    BalanceSheetReport,
    CompanySettingsUpdate,
    ContactCreate,
    EmployeeCreate,
    JournalEntryCreate,
    OperationalTransactionCreate,
    PayrollRunCreate,
    ProfitAndLossReport,
    PurchaseOrderCreate,
    ReceiptPayload,
)

RECEIPT_DIR = Path("data/raw/receipts")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def apply_local_schema_updates(db: Session) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    table_names = inspector.get_table_names()
    if "payroll_runs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("payroll_runs")}
        if "employee_id" not in columns:
            db.execute(text("ALTER TABLE payroll_runs ADD COLUMN employee_id INTEGER REFERENCES employees(id)"))
            db.commit()
    if "contacts" in table_names:
        columns = {column["name"] for column in inspector.get_columns("contacts")}
        contact_updates = [
            ("vendor_qualification_status", "VARCHAR(9) NOT NULL DEFAULT 'PENDING'"),
            ("payment_terms", "VARCHAR(80)"),
            ("default_expense_account_id", "INTEGER REFERENCES accounts(id)"),
            ("qualification_notes", "TEXT"),
            ("qualification_expires_on", "DATE"),
        ]
        for column_name, ddl in contact_updates:
            if column_name not in columns:
                db.execute(text(f"ALTER TABLE contacts ADD COLUMN {column_name} {ddl}"))
        db.commit()
    if "purchase_orders" in table_names:
        columns = {column["name"] for column in inspector.get_columns("purchase_orders")}
        if "payment_terms" not in columns:
            db.execute(text("ALTER TABLE purchase_orders ADD COLUMN payment_terms VARCHAR(120)"))
            db.commit()


def seed_company_settings(db: Session) -> None:
    if db.scalar(select(CompanySettings).limit(1)):
        return
    db.add(
        CompanySettings(
            company_name="IntelliArtAI",
            fiscal_year_start_month=1,
            base_currency="SGD",
        )
    )
    db.commit()


def get_company_settings(db: Session) -> CompanySettings:
    settings = db.scalar(select(CompanySettings).order_by(CompanySettings.id).limit(1))
    if settings is None:
        seed_company_settings(db)
        settings = db.scalar(select(CompanySettings).order_by(CompanySettings.id).limit(1))
    if settings is None:
        raise RuntimeError("Unable to initialize company settings.")
    return settings


def update_company_settings(db: Session, payload: CompanySettingsUpdate) -> CompanySettings:
    settings = get_company_settings(db)
    for key, value in payload.model_dump().items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


def create_contact(db: Session, payload: ContactCreate) -> Contact:
    if payload.default_expense_account_id is not None:
        account = _get_account(db, payload.default_expense_account_id)
        if account.type != AccountType.EXPENSE:
            raise ValueError("Default vendor expense account must be an expense account.")
    contact = Contact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def list_contacts(db: Session) -> list[Contact]:
    return list(db.scalars(select(Contact).order_by(Contact.name)).all())


def create_employee(db: Session, payload: EmployeeCreate) -> Employee:
    employee = Employee(**payload.model_dump())
    db.add(employee)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("Staff ID must be unique.") from exc
    db.refresh(employee)
    return employee


def list_employees(db: Session) -> list[Employee]:
    return list(db.scalars(select(Employee).order_by(Employee.status, Employee.name)).all())


def _safe_filename(filename: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return clean or "receipt"


def save_receipt(payload: ReceiptPayload) -> Receipt:
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except binascii.Error as exc:
        raise ValueError("Receipt content must be valid base64.") from exc
    if not content:
        raise ValueError("Receipt file cannot be empty.")
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("Receipt file cannot exceed 10 MB.")

    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}_{_safe_filename(payload.filename)}"
    stored_path = RECEIPT_DIR / stored_name
    stored_path.write_bytes(content)
    return Receipt(
        original_filename=payload.filename,
        stored_path=stored_path.as_posix(),
        content_type=payload.content_type,
        size_bytes=len(content),
    )


def _decimal_or_none(value) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _quantity_or_none(value) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value)).quantize(Decimal("0.001"))


def _confidence_or_none(value) -> Decimal | None:
    if value in (None, ""):
        return None
    confidence = Decimal(str(value))
    if confidence < 0:
        confidence = Decimal("0")
    if confidence > 1:
        confidence = Decimal("1")
    return confidence.quantize(Decimal("0.0001"))


def _date_or_none(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _amount_from_text(value: str) -> Decimal | None:
    clean = value.replace(",", "")
    match = re.search(r"(?:S\$|\$|SGD)?\s*([0-9]+(?:\.[0-9]{2}))", clean, re.IGNORECASE)
    if not match:
        return None
    return Decimal(match.group(1)).quantize(Decimal("0.01"))


def _date_from_text(value: str) -> str | None:
    patterns = [
        (r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", "%Y-%m-%d"),
        (r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", "%d-%m-%Y"),
    ]
    for pattern, date_format in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        normalized = "-".join(match.groups())
        try:
            return datetime.strptime(normalized, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_tesseract_receipt_text(raw_text: str) -> dict[str, object]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    total = None
    subtotal = None
    tax = None
    receipt_date = None
    currency = "SGD" if re.search(r"\bSGD\b|S\$|\$", raw_text, re.IGNORECASE) else None
    line_items = []

    skip_line_item = re.compile(r"\b(total|subtotal|gst|tax|visa|mastercard|cash|change|paid|balance)\b", re.IGNORECASE)
    for line in lines:
        receipt_date = receipt_date or _date_from_text(line)
        amount = _amount_from_text(line)
        if amount is None:
            continue
        lower = line.lower()
        if "subtotal" in lower:
            subtotal = amount
        elif "gst" in lower or "tax" in lower:
            tax = amount
        elif "total" in lower or "amount due" in lower:
            total = amount
        elif not skip_line_item.search(line):
            description = re.sub(r"(?:S\$|\$|SGD)?\s*[0-9,]+\.[0-9]{2}\s*$", "", line, flags=re.IGNORECASE).strip(" -:")
            if description:
                line_items.append(
                    {
                        "description": description[:240],
                        "quantity": None,
                        "unit_price": None,
                        "amount": amount,
                        "confidence": 0.55,
                    }
                )

    if total is None:
        amounts = [_amount_from_text(line) for line in lines]
        amounts = [amount for amount in amounts if amount is not None]
        total = max(amounts) if amounts else None

    merchant_name = None
    for line in lines[:6]:
        if _date_from_text(line) or _amount_from_text(line) or skip_line_item.search(line):
            continue
        merchant_name = line[:180]
        break

    return {
        "merchant_name": merchant_name,
        "receipt_date": receipt_date,
        "currency": currency,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "confidence": 0.55 if raw_text.strip() else 0.0,
        "raw_text": raw_text,
        "line_items": line_items[:20],
    }


def _clear_extraction(extraction: ReceiptExtraction) -> None:
    extraction.merchant_name = None
    extraction.receipt_date = None
    extraction.currency = None
    extraction.subtotal = None
    extraction.tax = None
    extraction.total = None
    extraction.confidence = None
    extraction.raw_text = None
    extraction.error_message = None
    extraction.line_items.clear()


def _receipt_content(receipt: Receipt) -> tuple[str, str]:
    content_type = receipt.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise ValueError("Receipt extraction currently supports image uploads such as JPG, PNG, or HEIC.")
    file_path = Path(receipt.stored_path)
    if not file_path.exists():
        raise ValueError("Stored receipt file was not found.")
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return content_type, encoded


def _receipt_extraction_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "merchant_name",
            "receipt_date",
            "currency",
            "subtotal",
            "tax",
            "total",
            "confidence",
            "raw_text",
            "line_items",
        ],
        "properties": {
            "merchant_name": {"type": ["string", "null"]},
            "receipt_date": {"type": ["string", "null"], "description": "Receipt date in YYYY-MM-DD format."},
            "currency": {"type": ["string", "null"], "description": "ISO 4217 currency code if visible."},
            "subtotal": {"type": ["number", "null"]},
            "tax": {"type": ["number", "null"]},
            "total": {"type": ["number", "null"]},
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "raw_text": {"type": ["string", "null"], "description": "Visible receipt text transcribed from the image."},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["description", "quantity", "unit_price", "amount", "confidence"],
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": ["number", "null"]},
                        "unit_price": {"type": ["number", "null"]},
                        "amount": {"type": ["number", "null"]},
                        "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                    },
                },
            },
        },
    }


def _ollama_generate_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/generate"


def _extract_with_openai(receipt: Receipt) -> dict[str, object]:
    from .config import get_settings

    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("Set OPENAI_API_KEY in .env to enable receipt OCR extraction.")

    content_type, encoded = _receipt_content(receipt)
    prompt = (
        "Extract bookkeeping details from this receipt image. "
        "Return only fields visible or strongly inferable from the receipt. "
        "Use null for uncertain missing values. Do not invent line items."
    )
    body = {
        "model": settings.receipt_extraction_model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:{content_type};base64,{encoded}"},
                ],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "receipt_extraction",
                "strict": True,
                "schema": _receipt_extraction_schema(),
            }
        },
    }
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Receipt extraction provider returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Receipt extraction provider is unreachable: {exc.reason}") from exc

    output_text = response_body.get("output_text")
    if output_text is None:
        for item in response_body.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    output_text = content["text"]
                    break
            if output_text:
                break
    if not output_text:
        raise RuntimeError("Receipt extraction provider returned no structured output.")
    return json.loads(output_text)


def _extract_with_tesseract(receipt: Receipt) -> dict[str, object]:
    from .config import get_settings

    settings = get_settings()
    _receipt_content(receipt)
    try:
        result = subprocess.run(
            [settings.tesseract_cmd, receipt.stored_path, "stdout", "--psm", "6"],
            capture_output=True,
            check=False,
            text=True,
            timeout=45,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Tesseract was not found. Set TESSERACT_CMD in .env or add tesseract to PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Tesseract receipt extraction timed out.") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or "Unknown Tesseract error."
        raise RuntimeError(f"Tesseract receipt extraction failed: {detail}")
    return _parse_tesseract_receipt_text(result.stdout)


def _extract_with_tesseract_ollama(receipt: Receipt) -> dict[str, object]:
    from .config import get_settings

    settings = get_settings()
    tesseract_data = _extract_with_tesseract(receipt)
    raw_text = tesseract_data.get("raw_text") or ""
    if not raw_text.strip():
        return tesseract_data

    prompt = f"""
Convert this OCR text from a business receipt into structured bookkeeping JSON.

Rules:
- Use only values present in the OCR text.
- Use null when a value is missing or uncertain.
- Dates must be YYYY-MM-DD.
- Currency should be an ISO 4217 code, for example SGD.
- Line items should be purchasable goods/services only, not payment method, subtotal, tax, total, or change lines.
- Confidence must be between 0 and 1.

OCR text:
{raw_text}
""".strip()
    body = {
        "model": settings.ollama_receipt_model,
        "prompt": prompt,
        "stream": False,
        "format": _receipt_extraction_schema(),
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        _ollama_generate_url(settings.ollama_base_url),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama receipt parser returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama receipt parser is unreachable: {exc.reason}") from exc

    response_text = response_body.get("response")
    if not response_text:
        raise RuntimeError("Ollama receipt parser returned no JSON response.")
    parsed = json.loads(response_text)
    parsed["raw_text"] = raw_text
    return parsed


def extract_receipt_details(db: Session, receipt_id: int) -> ReceiptExtraction:
    receipt = db.scalar(
        select(Receipt)
        .options(selectinload(Receipt.extraction).selectinload(ReceiptExtraction.line_items))
        .where(Receipt.id == receipt_id)
    )
    if receipt is None:
        raise ValueError(f"Unknown receipt id: {receipt_id}")

    extraction = receipt.extraction
    if extraction is None:
        extraction = ReceiptExtraction(receipt_id=receipt.id, status=ReceiptExtractionStatus.FAILED, provider="openai")
        db.add(extraction)
        db.flush()
    _clear_extraction(extraction)

    from .config import get_settings

    settings = get_settings()
    provider = settings.receipt_extraction_provider.lower()
    extraction.provider = provider
    if provider == "openai":
        extraction.model = settings.receipt_extraction_model
    elif provider == "tesseract_ollama":
        extraction.model = settings.ollama_receipt_model
    else:
        extraction.model = "tesseract"
    try:
        if provider == "openai":
            data = _extract_with_openai(receipt)
        elif provider == "tesseract_ollama":
            data = _extract_with_tesseract_ollama(receipt)
        elif provider == "tesseract":
            data = _extract_with_tesseract(receipt)
        else:
            raise RuntimeError(f"Unsupported receipt extraction provider: {settings.receipt_extraction_provider}")
    except RuntimeError as exc:
        extraction.status = (
            ReceiptExtractionStatus.NOT_CONFIGURED
            if "OPENAI_API_KEY" in str(exc) or "Tesseract was not found" in str(exc)
            else ReceiptExtractionStatus.FAILED
        )
        extraction.error_message = str(exc)
        db.commit()
        db.refresh(extraction)
        return extraction
    except ValueError as exc:
        extraction.status = ReceiptExtractionStatus.FAILED
        extraction.error_message = str(exc)
        db.commit()
        db.refresh(extraction)
        return extraction

    extraction.status = ReceiptExtractionStatus.COMPLETED
    extraction.merchant_name = data.get("merchant_name")
    extraction.receipt_date = _date_or_none(data.get("receipt_date"))
    extraction.currency = (data.get("currency") or None)
    extraction.subtotal = _decimal_or_none(data.get("subtotal"))
    extraction.tax = _decimal_or_none(data.get("tax"))
    extraction.total = _decimal_or_none(data.get("total"))
    extraction.confidence = _confidence_or_none(data.get("confidence"))
    extraction.raw_text = data.get("raw_text")
    for item in data.get("line_items") or []:
        description = item.get("description")
        if not description:
            continue
        extraction.line_items.append(
            ReceiptLineItem(
                description=description[:240],
                quantity=_quantity_or_none(item.get("quantity")),
                unit_price=_decimal_or_none(item.get("unit_price")),
                amount=_decimal_or_none(item.get("amount")),
                confidence=_confidence_or_none(item.get("confidence")),
            )
        )
    db.commit()
    db.refresh(extraction)
    return extraction


def _get_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise ValueError(f"Unknown account id: {account_id}")
    return account


def _get_account_by_code(db: Session, code: str) -> Account:
    account = db.scalar(select(Account).where(Account.code == code))
    if account is None:
        raise ValueError(f"Missing required account code: {code}")
    return account


def _validate_operational_accounts(kind: TransactionKind, debit_account: Account, credit_account: Account) -> None:
    if kind == TransactionKind.EXPENSE:
        if debit_account.type != AccountType.EXPENSE:
            raise ValueError("Expense transactions must debit an expense account.")
        if credit_account.type not in {AccountType.ASSET, AccountType.LIABILITY}:
            raise ValueError("Expense transactions must credit cash/bank or accounts payable.")
    if kind == TransactionKind.INCOME:
        if debit_account.type != AccountType.ASSET:
            raise ValueError("Income transactions must debit cash/bank or accounts receivable.")
        if credit_account.type != AccountType.REVENUE:
            raise ValueError("Income transactions must credit a revenue account.")


def create_operational_transaction(db: Session, payload: OperationalTransactionCreate) -> OperationalTransaction:
    debit_account = _get_account(db, payload.debit_account_id)
    credit_account = _get_account(db, payload.credit_account_id)
    _validate_operational_accounts(payload.kind, debit_account, credit_account)

    if payload.contact_id is not None and db.get(Contact, payload.contact_id) is None:
        raise ValueError(f"Unknown contact id: {payload.contact_id}")

    receipt = save_receipt(payload.receipt) if payload.receipt else None
    transaction = OperationalTransaction(
        kind=payload.kind,
        status=payload.status,
        transaction_date=payload.transaction_date,
        description=payload.description,
        reference=payload.reference,
        amount=payload.amount,
        contact_id=payload.contact_id,
        debit_account_id=payload.debit_account_id,
        credit_account_id=payload.credit_account_id,
        receipt=receipt,
    )
    db.add(transaction)
    db.flush()

    if transaction.status == TransactionStatus.POSTED:
        _post_operational_transaction(db, transaction)

    db.commit()
    return get_operational_transaction(db, transaction.id)


def _post_operational_transaction(db: Session, transaction: OperationalTransaction) -> None:
    entry = create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=transaction.transaction_date,
            memo=transaction.description,
            reference=transaction.reference,
            lines=[
                {
                    "account_id": transaction.debit_account_id,
                    "debit": transaction.amount,
                    "description": transaction.description,
                },
                {
                    "account_id": transaction.credit_account_id,
                    "credit": transaction.amount,
                    "description": transaction.description,
                },
            ],
        ),
        commit=False,
    )
    transaction.journal_entry_id = entry.id
    transaction.status = TransactionStatus.POSTED
    transaction.posted_at = datetime.now(UTC)


def post_operational_transaction(db: Session, transaction_id: int) -> OperationalTransaction:
    transaction = db.get(OperationalTransaction, transaction_id)
    if transaction is None:
        raise ValueError(f"Unknown transaction id: {transaction_id}")
    if transaction.status == TransactionStatus.POSTED:
        return get_operational_transaction(db, transaction.id)
    _post_operational_transaction(db, transaction)
    db.commit()
    return get_operational_transaction(db, transaction.id)


def get_operational_transaction(db: Session, transaction_id: int) -> OperationalTransaction:
    transaction = db.scalar(
        transaction_query().where(OperationalTransaction.id == transaction_id)
    )
    if transaction is None:
        raise ValueError(f"Unknown transaction id: {transaction_id}")
    return transaction


def transaction_query():
    return select(OperationalTransaction).options(
        selectinload(OperationalTransaction.contact),
        selectinload(OperationalTransaction.debit_account),
        selectinload(OperationalTransaction.credit_account),
        selectinload(OperationalTransaction.receipt)
        .selectinload(Receipt.extraction)
        .selectinload(ReceiptExtraction.line_items),
    )


def list_operational_transactions(db: Session, limit: int = 50) -> list[OperationalTransaction]:
    return list(
        db.scalars(
            transaction_query().order_by(
                OperationalTransaction.transaction_date.desc(),
                OperationalTransaction.id.desc(),
            ).limit(limit)
        ).all()
    )


def _generate_po_number(db: Session, issue_date) -> str:
    prefix = f"PO-{issue_date:%Y%m}"
    count = db.scalar(select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.po_number.like(f"{prefix}-%"))) or 0
    return f"{prefix}-{count + 1:04d}"


def _validate_vendor_for_po(vendor: Contact, issuing: bool = False) -> None:
    if vendor.type not in {ContactType.VENDOR, ContactType.BOTH}:
        raise ValueError("Purchase orders can only be assigned to vendor contacts.")
    if issuing and vendor.vendor_qualification_status != VendorQualificationStatus.QUALIFIED:
        raise ValueError("Purchase orders can only be issued to qualified vendors.")


def _validate_purchase_order_lines(db: Session, payload: PurchaseOrderCreate) -> None:
    for line in payload.lines:
        account = _get_account(db, line.expense_account_id)
        if account.type != AccountType.EXPENSE:
            raise ValueError("Purchase order lines must use expense accounts.")


def purchase_order_query():
    return select(PurchaseOrder).options(
        selectinload(PurchaseOrder.vendor),
        selectinload(PurchaseOrder.lines).selectinload(PurchaseOrderLine.expense_account),
    )


def get_purchase_order(db: Session, purchase_order_id: int) -> PurchaseOrder:
    purchase_order = db.scalar(purchase_order_query().where(PurchaseOrder.id == purchase_order_id))
    if purchase_order is None:
        raise ValueError(f"Unknown purchase order id: {purchase_order_id}")
    return purchase_order


def list_purchase_orders(db: Session, limit: int = 50) -> list[PurchaseOrder]:
    return list(
        db.scalars(
            purchase_order_query().order_by(
                PurchaseOrder.issue_date.desc(),
                PurchaseOrder.id.desc(),
            ).limit(limit)
        ).all()
    )


def create_purchase_order(db: Session, payload: PurchaseOrderCreate) -> PurchaseOrder:
    vendor = db.get(Contact, payload.vendor_id)
    if vendor is None:
        raise ValueError(f"Unknown vendor id: {payload.vendor_id}")
    _validate_vendor_for_po(vendor, issuing=payload.status == PurchaseOrderStatus.ISSUED)
    _validate_purchase_order_lines(db, payload)

    purchase_order = PurchaseOrder(
        po_number=payload.po_number or _generate_po_number(db, payload.issue_date),
        status=payload.status,
        vendor_id=payload.vendor_id,
        issue_date=payload.issue_date,
        expected_delivery_date=payload.expected_delivery_date,
        currency=payload.currency,
        payment_terms=payload.payment_terms,
        notes=payload.notes,
        delivery_instructions=payload.delivery_instructions,
    )
    if purchase_order.status == PurchaseOrderStatus.ISSUED:
        purchase_order.issued_at = datetime.now(UTC)
    for line in payload.lines:
        purchase_order.lines.append(PurchaseOrderLine(**line.model_dump()))
    db.add(purchase_order)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("PO number must be unique.") from exc
    return get_purchase_order(db, purchase_order.id)


def issue_purchase_order(db: Session, purchase_order_id: int) -> PurchaseOrder:
    purchase_order = db.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        raise ValueError(f"Unknown purchase order id: {purchase_order_id}")
    if purchase_order.status == PurchaseOrderStatus.ISSUED:
        return get_purchase_order(db, purchase_order.id)
    if purchase_order.status != PurchaseOrderStatus.DRAFT:
        raise ValueError("Only draft purchase orders can be issued.")
    vendor = db.get(Contact, purchase_order.vendor_id)
    if vendor is None:
        raise ValueError("Purchase order vendor was not found.")
    _validate_vendor_for_po(vendor, issuing=True)
    purchase_order.status = PurchaseOrderStatus.ISSUED
    purchase_order.issued_at = datetime.now(UTC)
    db.commit()
    return get_purchase_order(db, purchase_order.id)


def cancel_purchase_order(db: Session, purchase_order_id: int) -> PurchaseOrder:
    purchase_order = db.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        raise ValueError(f"Unknown purchase order id: {purchase_order_id}")
    if purchase_order.status in {PurchaseOrderStatus.CLOSED, PurchaseOrderStatus.CANCELLED}:
        return get_purchase_order(db, purchase_order.id)
    if purchase_order.status in {PurchaseOrderStatus.BILLED, PurchaseOrderStatus.RECEIVED}:
        raise ValueError("Billed or received purchase orders cannot be cancelled here.")
    purchase_order.status = PurchaseOrderStatus.CANCELLED
    purchase_order.cancelled_at = datetime.now(UTC)
    db.commit()
    return get_purchase_order(db, purchase_order.id)


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _round_cpf_total(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP).quantize(Decimal("0.01"))


def _round_employee_cpf(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_FLOOR).quantize(Decimal("0.01"))


def payroll_query():
    return select(PayrollRun).options(
        selectinload(PayrollRun.employee),
        selectinload(PayrollRun.salary_account),
        selectinload(PayrollRun.employer_cpf_account),
        selectinload(PayrollRun.cash_account),
        selectinload(PayrollRun.cpf_payable_account),
    )


def list_payroll_runs(db: Session, limit: int = 50) -> list[PayrollRun]:
    return list(
        db.scalars(
            payroll_query().order_by(
                PayrollRun.pay_date.desc(),
                PayrollRun.id.desc(),
            ).limit(limit)
        ).all()
    )


def get_payroll_run(db: Session, payroll_id: int) -> PayrollRun:
    payroll = db.scalar(payroll_query().where(PayrollRun.id == payroll_id))
    if payroll is None:
        raise ValueError(f"Unknown payroll id: {payroll_id}")
    return payroll


def _validate_payroll_accounts(
    salary_account: Account,
    employer_cpf_account: Account,
    cash_account: Account,
    cpf_payable_account: Account,
) -> None:
    if salary_account.type != AccountType.EXPENSE:
        raise ValueError("Payroll must debit a salary expense account.")
    if employer_cpf_account.type != AccountType.EXPENSE:
        raise ValueError("Payroll must debit an employer CPF expense account.")
    if cash_account.type != AccountType.ASSET:
        raise ValueError("Payroll net pay must credit a cash or bank account.")
    if cpf_payable_account.type != AccountType.LIABILITY:
        raise ValueError("Payroll CPF must credit a CPF payable liability account.")


def create_payroll_run(db: Session, payload: PayrollRunCreate) -> PayrollRun:
    employee = None
    if payload.employee_id is not None:
        employee = db.get(Employee, payload.employee_id)
        if employee is None:
            raise ValueError(f"Unknown employee id: {payload.employee_id}")

    salary_account = _get_account(db, payload.salary_account_id)
    employer_cpf_account = _get_account(db, payload.employer_cpf_account_id)
    cash_account = _get_account(db, payload.cash_account_id)
    cpf_payable_account = _get_account(db, payload.cpf_payable_account_id)
    _validate_payroll_accounts(salary_account, employer_cpf_account, cash_account, cpf_payable_account)

    cpf_subject_wage = payload.cpf_subject_wage
    if cpf_subject_wage is None:
        cpf_subject_wage = min(payload.gross_salary, Decimal("8000.00"))
    cpf_subject_wage = _round_money(cpf_subject_wage)

    employee_cpf = _round_employee_cpf(cpf_subject_wage * payload.employee_cpf_rate)
    total_cpf = _round_cpf_total(cpf_subject_wage * (payload.employee_cpf_rate + payload.employer_cpf_rate))
    employer_cpf = _round_money(total_cpf - employee_cpf)
    net_pay = _round_money(payload.gross_salary - employee_cpf)
    if net_pay < 0:
        raise ValueError("Employee CPF cannot exceed gross salary.")

    payroll = PayrollRun(
        status=payload.status,
        employee_id=payload.employee_id,
        employee_name=payload.employee_name,
        period_start=payload.period_start,
        period_end=payload.period_end,
        pay_date=payload.pay_date,
        gross_salary=payload.gross_salary,
        cpf_subject_wage=cpf_subject_wage,
        employee_cpf_rate=payload.employee_cpf_rate,
        employer_cpf_rate=payload.employer_cpf_rate,
        employee_cpf=employee_cpf,
        employer_cpf=employer_cpf,
        net_pay=net_pay,
        salary_account_id=payload.salary_account_id,
        employer_cpf_account_id=payload.employer_cpf_account_id,
        cash_account_id=payload.cash_account_id,
        cpf_payable_account_id=payload.cpf_payable_account_id,
        notes=payload.notes,
    )
    db.add(payroll)
    db.flush()

    if payroll.status == PayrollStatus.POSTED:
        _post_payroll_run(db, payroll)

    db.commit()
    return get_payroll_run(db, payroll.id)


def _post_payroll_run(db: Session, payroll: PayrollRun) -> None:
    cpf_payable = _round_money(payroll.employee_cpf + payroll.employer_cpf)
    lines = [
        {
            "account_id": payroll.salary_account_id,
            "debit": payroll.gross_salary,
            "description": f"Gross salary for {payroll.employee_name}",
        },
        {
            "account_id": payroll.cash_account_id,
            "credit": payroll.net_pay,
            "description": f"Net pay for {payroll.employee_name}",
        },
    ]
    if payroll.employer_cpf > 0:
        lines.append(
            {
                "account_id": payroll.employer_cpf_account_id,
                "debit": payroll.employer_cpf,
                "description": f"Employer CPF for {payroll.employee_name}",
            }
        )
    if cpf_payable > 0:
        lines.append(
            {
                "account_id": payroll.cpf_payable_account_id,
                "credit": cpf_payable,
                "description": f"CPF payable for {payroll.employee_name}",
            }
        )
    entry = create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=payroll.pay_date,
            memo=f"Payroll - {payroll.employee_name}",
            reference=f"PAY-{payroll.id}",
            lines=lines,
        ),
        commit=False,
    )
    payroll.journal_entry_id = entry.id
    payroll.status = PayrollStatus.POSTED
    payroll.posted_at = datetime.now(UTC)


def post_payroll_run(db: Session, payroll_id: int) -> PayrollRun:
    payroll = db.get(PayrollRun, payroll_id)
    if payroll is None:
        raise ValueError(f"Unknown payroll id: {payroll_id}")
    if payroll.status == PayrollStatus.POSTED:
        return get_payroll_run(db, payroll.id)
    _post_payroll_run(db, payroll)
    db.commit()
    return get_payroll_run(db, payroll.id)


def account_read(account: Account, balance) -> AccountRead:
    return AccountRead.model_validate(account).model_copy(update={"balance": balance})


def profit_and_loss(db: Session) -> ProfitAndLossReport:
    accounts = list_accounts_with_balances(db)
    revenue_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.REVENUE]
    expense_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.EXPENSE]
    revenue = sum(balance for _, balance in revenue_accounts)
    expenses = sum(balance for _, balance in expense_accounts)
    return ProfitAndLossReport(
        revenue=revenue,
        expenses=expenses,
        net_income=revenue - expenses,
        revenue_accounts=[account_read(account, balance) for account, balance in revenue_accounts],
        expense_accounts=[account_read(account, balance) for account, balance in expense_accounts],
    )


def balance_sheet(db: Session) -> BalanceSheetReport:
    accounts = list_accounts_with_balances(db)
    pnl = profit_and_loss(db)
    asset_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.ASSET]
    liability_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.LIABILITY]
    equity_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.EQUITY]
    assets = sum(balance for _, balance in asset_accounts)
    liabilities = sum(balance for _, balance in liability_accounts)
    equity = sum(balance for _, balance in equity_accounts)
    retained_earnings = pnl.net_income
    return BalanceSheetReport(
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        retained_earnings=retained_earnings,
        total_liabilities_and_equity=liabilities + equity + retained_earnings,
        asset_accounts=[account_read(account, balance) for account, balance in asset_accounts],
        liability_accounts=[account_read(account, balance) for account, balance in liability_accounts],
        equity_accounts=[account_read(account, balance) for account, balance in equity_accounts],
    )
