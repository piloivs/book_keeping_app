import base64
import binascii
import json
import re
import subprocess
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session, selectinload

from .accounting import create_journal_entry, list_accounts_with_balances
from .database import Base
from .models import (
    Account,
    AccountType,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    BankStatementLine,
    BankStatementLineStatus,
    CompanySettings,
    Contact,
    ContactType,
    CustomerReceipt,
    CustomerReceiptAllocation,
    CustomerReceiptStatus,
    DepositStatus,
    Employee,
    JournalEntry,
    JournalLine,
    PayrollRun,
    PayrollStatus,
    Project,
    ProjectStatus,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    Receipt,
    ReceiptExtraction,
    ReceiptExtractionStatus,
    ReceiptLineItem,
    SalesInvoice,
    SalesInvoiceLine,
    SalesInvoiceStatus,
    SalesOrder,
    SalesOrderLine,
    SalesOrderStatus,
    SupplierBill,
    SupplierBillLine,
    SupplierBillStatus,
    SupplierPayment,
    SupplierPaymentAllocation,
    SupplierPaymentStatus,
    TransactionKind,
    TransactionStatus,
    OperationalTransaction,
    VendorQualificationStatus,
)
from .schemas import (
    AccountRead,
    AccountsPayableAgeingReport,
    AccountsPayableAgeingRow,
    AccountsReceivableAgeingReport,
    AccountsReceivableAgeingRow,
    ApprovalDecision,
    ApprovalRequestCreate,
    AuditEventRead,
    BankReconciliationSummary,
    BankStatementLineCreate,
    BalanceSheetReport,
    ClientHistoryEntry,
    ClientHistoryReport,
    CompanySettingsUpdate,
    ContactCreate,
    EmployeeCreate,
    JournalEntryCreate,
    CustomerReceiptCreate,
    OperationalTransactionCreate,
    PayrollRunCreate,
    ProjectCreate,
    ProjectProfitabilityReport,
    ProjectProfitabilityRow,
    ProfitAndLossReport,
    PurchaseOrderCreate,
    ReceiptPayload,
    SalesInvoiceCreate,
    SalesOrderCreate,
    SupplierBillCreate,
    SupplierPaymentCreate,
)

RECEIPT_DIR = Path("data/raw/receipts")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def _export_json_default(value: object) -> str:
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    return str(value)


def create_backup_export(db: Session) -> tuple[str, bytes]:
    generated_at = datetime.now(UTC)
    buffer = BytesIO()
    table_names: list[str] = []
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest = {
            "app": "IntelliArtAI Operations Core",
            "generated_at": generated_at.isoformat(),
            "format": "json-table-export-v1",
            "tables": [],
        }
        for table in Base.metadata.sorted_tables:
            rows = [dict(row) for row in db.execute(select(table)).mappings().all()]
            table_names.append(table.name)
            manifest["tables"].append({"name": table.name, "rows": len(rows)})
            archive.writestr(
                f"data/{table.name}.json",
                json.dumps(rows, default=_export_json_default, indent=2, sort_keys=True),
            )
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        archive.writestr(
            "README.txt",
            "This export contains structured JSON snapshots of bookkeeping app tables. "
            "It is intended for backup, review, and accountant handoff, not direct re-import.\n",
        )
    filename = f"intelliartai-bookkeeping-export-{generated_at:%Y%m%d-%H%M%S}.zip"
    return filename, buffer.getvalue()


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
    if "sales_orders" in table_names:
        columns = {column["name"] for column in inspector.get_columns("sales_orders")}
        sales_order_updates = [
            ("deposit_required", "BOOLEAN NOT NULL DEFAULT 0"),
            ("deposit_rate", "NUMERIC(6, 4) NOT NULL DEFAULT 0.0000"),
            ("deposit_amount", "NUMERIC(12, 2) NOT NULL DEFAULT 0.00"),
            ("deposit_due_date", "DATE"),
            ("deposit_status", "VARCHAR(13) NOT NULL DEFAULT 'NOT_REQUESTED'"),
            ("deposit_transaction_id", "INTEGER REFERENCES operational_transactions(id)"),
            ("project_id", "INTEGER REFERENCES projects(id)"),
        ]
        for column_name, ddl in sales_order_updates:
            if column_name not in columns:
                db.execute(text(f"ALTER TABLE sales_orders ADD COLUMN {column_name} {ddl}"))
        db.commit()
    if "operational_transactions" in table_names:
        columns = {column["name"] for column in inspector.get_columns("operational_transactions")}
        if "project_id" not in columns:
            db.execute(text("ALTER TABLE operational_transactions ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
            db.commit()
    if "sales_invoices" in table_names:
        columns = {column["name"] for column in inspector.get_columns("sales_invoices")}
        if "project_id" not in columns:
            db.execute(text("ALTER TABLE sales_invoices ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
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


def create_project(db: Session, payload: ProjectCreate) -> Project:
    client = db.get(Contact, payload.client_id)
    if client is None:
        raise ValueError(f"Unknown client id: {payload.client_id}")
    if client.type not in {ContactType.CUSTOMER, ContactType.BOTH}:
        raise ValueError("Project client must be a customer or both-type contact.")
    project = Project(**payload.model_dump())
    db.add(project)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("Project code must be unique.") from exc
    return get_project(db, project.id)


def project_query():
    return select(Project).options(selectinload(Project.client))


def get_project(db: Session, project_id: int) -> Project:
    project = db.scalar(project_query().where(Project.id == project_id))
    if project is None:
        raise ValueError(f"Unknown project id: {project_id}")
    return project


def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(project_query().order_by(Project.status, Project.project_code)).all())


def _validate_project_for_customer(db: Session, project_id: int | None, customer_id: int) -> Project | None:
    if project_id is None:
        return None
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Unknown project id: {project_id}")
    if project.client_id != customer_id:
        raise ValueError("Project client must match the customer.")
    if project.status == ProjectStatus.CANCELLED:
        raise ValueError("Cancelled projects cannot be linked to new activity.")
    return project


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
    if kind == TransactionKind.DEPOSIT:
        if debit_account.type != AccountType.ASSET:
            raise ValueError("Deposit transactions must debit cash/bank or accounts receivable.")
        if credit_account.type != AccountType.LIABILITY:
            raise ValueError("Deposit transactions must credit a liability account.")


def create_operational_transaction(db: Session, payload: OperationalTransactionCreate) -> OperationalTransaction:
    debit_account = _get_account(db, payload.debit_account_id)
    credit_account = _get_account(db, payload.credit_account_id)
    _validate_operational_accounts(payload.kind, debit_account, credit_account)

    if payload.contact_id is not None and db.get(Contact, payload.contact_id) is None:
        raise ValueError(f"Unknown contact id: {payload.contact_id}")
    if payload.project_id is not None:
        project = db.get(Project, payload.project_id)
        if project is None:
            raise ValueError(f"Unknown project id: {payload.project_id}")
        if payload.kind in {TransactionKind.INCOME, TransactionKind.DEPOSIT} and payload.contact_id is not None and project.client_id != payload.contact_id:
            raise ValueError("Income or deposit project must match the customer contact.")

    receipt = save_receipt(payload.receipt) if payload.receipt else None
    transaction = OperationalTransaction(
        kind=payload.kind,
        status=payload.status,
        transaction_date=payload.transaction_date,
        description=payload.description,
        reference=payload.reference,
        amount=payload.amount,
        contact_id=payload.contact_id,
        project_id=payload.project_id,
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
    transaction._allow_accounting_post_mutation = True
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
        selectinload(OperationalTransaction.project).selectinload(Project.client),
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


def _record_audit_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: int | None,
    action: str,
    summary: str,
    actor: str | None = None,
    details: dict[str, object] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        summary=summary,
        details_json=json.dumps(details, default=str, sort_keys=True) if details else None,
    )
    db.add(event)
    return event


def list_audit_events(db: Session, limit: int = 100) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .limit(limit)
        ).all()
    )


def approval_request_query():
    return select(ApprovalRequest)


def list_approval_requests(
    db: Session,
    *,
    status: ApprovalStatus | None = None,
    limit: int = 100,
) -> list[ApprovalRequest]:
    query = approval_request_query()
    if status is not None:
        query = query.where(ApprovalRequest.status == status)
    return list(
        db.scalars(
            query.order_by(
                ApprovalRequest.requested_at.desc(),
                ApprovalRequest.id.desc(),
            ).limit(limit)
        ).all()
    )


def _latest_approval_request(db: Session, document_type: str, document_id: int, action: str) -> ApprovalRequest | None:
    return db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.document_type == document_type)
        .where(ApprovalRequest.document_id == document_id)
        .where(ApprovalRequest.action == action)
        .order_by(ApprovalRequest.requested_at.desc(), ApprovalRequest.id.desc())
        .limit(1)
    )


def request_approval(db: Session, payload: ApprovalRequestCreate) -> ApprovalRequest:
    existing = _latest_approval_request(db, payload.document_type, payload.document_id, payload.action)
    if existing is not None and existing.status == ApprovalStatus.PENDING:
        return existing
    request = ApprovalRequest(**payload.model_dump())
    db.add(request)
    db.flush()
    _record_audit_event(
        db,
        entity_type="approval_request",
        entity_id=request.id,
        action="requested",
        actor=payload.requested_by,
        summary=f"Approval requested for {payload.document_type} #{payload.document_id}.",
        details={
            "document_type": payload.document_type,
            "document_id": payload.document_id,
            "approval_action": payload.action,
        },
    )
    db.commit()
    db.refresh(request)
    return request


def approve_request(db: Session, request_id: int, payload: ApprovalDecision) -> ApprovalRequest:
    request = db.get(ApprovalRequest, request_id)
    if request is None:
        raise ValueError(f"Unknown approval request id: {request_id}")
    if request.status != ApprovalStatus.PENDING:
        return request
    request.status = ApprovalStatus.APPROVED
    request.decided_by = payload.decided_by
    request.decision_notes = payload.decision_notes
    request.decided_at = datetime.now(UTC)
    _record_audit_event(
        db,
        entity_type="approval_request",
        entity_id=request.id,
        action="approved",
        actor=payload.decided_by,
        summary=f"Approval request {request.id} approved.",
        details={
            "document_type": request.document_type,
            "document_id": request.document_id,
            "approval_action": request.action,
        },
    )
    db.commit()
    db.refresh(request)
    return request


def reject_request(db: Session, request_id: int, payload: ApprovalDecision) -> ApprovalRequest:
    request = db.get(ApprovalRequest, request_id)
    if request is None:
        raise ValueError(f"Unknown approval request id: {request_id}")
    if request.status != ApprovalStatus.PENDING:
        return request
    request.status = ApprovalStatus.REJECTED
    request.decided_by = payload.decided_by
    request.decision_notes = payload.decision_notes
    request.decided_at = datetime.now(UTC)
    _record_audit_event(
        db,
        entity_type="approval_request",
        entity_id=request.id,
        action="rejected",
        actor=payload.decided_by,
        summary=f"Approval request {request.id} rejected.",
        details={
            "document_type": request.document_type,
            "document_id": request.document_id,
            "approval_action": request.action,
        },
    )
    db.commit()
    db.refresh(request)
    return request


def _ensure_approval_allows_action(db: Session, document_type: str, document_id: int, action: str = "post") -> None:
    request = _latest_approval_request(db, document_type, document_id, action)
    if request is None:
        return
    if request.status == ApprovalStatus.APPROVED:
        return
    if request.status == ApprovalStatus.PENDING:
        raise ValueError("This document is awaiting approval before posting.")
    raise ValueError("This document was rejected and cannot be posted without a new approved request.")


def bank_statement_line_query():
    return select(BankStatementLine).options(
        selectinload(BankStatementLine.bank_account),
        selectinload(BankStatementLine.journal_entry).selectinload(JournalEntry.lines).selectinload(JournalLine.account),
    )


def get_bank_statement_line(db: Session, line_id: int) -> BankStatementLine:
    line = db.scalar(bank_statement_line_query().where(BankStatementLine.id == line_id))
    if line is None:
        raise ValueError(f"Unknown bank statement line id: {line_id}")
    return line


def list_bank_statement_lines(
    db: Session,
    *,
    bank_account_id: int | None = None,
    status: BankStatementLineStatus | None = None,
    limit: int = 100,
) -> list[BankStatementLine]:
    query = bank_statement_line_query()
    if bank_account_id is not None:
        query = query.where(BankStatementLine.bank_account_id == bank_account_id)
    if status is not None:
        query = query.where(BankStatementLine.status == status)
    return list(
        db.scalars(
            query.order_by(
                BankStatementLine.statement_date.desc(),
                BankStatementLine.id.desc(),
            ).limit(limit)
        ).all()
    )


def create_bank_statement_line(db: Session, payload: BankStatementLineCreate) -> BankStatementLine:
    bank_account = _get_account(db, payload.bank_account_id)
    if bank_account.type != AccountType.ASSET:
        raise ValueError("Bank statement lines must be assigned to a bank or cash asset account.")
    line = BankStatementLine(
        bank_account_id=payload.bank_account_id,
        statement_date=payload.statement_date,
        description=payload.description,
        reference=payload.reference,
        amount=payload.amount,
        notes=payload.notes,
    )
    db.add(line)
    db.commit()
    return get_bank_statement_line(db, line.id)


def _journal_entry_bank_amount(entry: JournalEntry, bank_account_id: int) -> Decimal:
    return sum(
        (
            line.debit - line.credit
            for line in entry.lines
            if line.account_id == bank_account_id
        ),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))


def reconcile_bank_statement_line(db: Session, line_id: int, journal_entry_id: int) -> BankStatementLine:
    line = db.get(BankStatementLine, line_id)
    if line is None:
        raise ValueError(f"Unknown bank statement line id: {line_id}")
    if line.status == BankStatementLineStatus.RECONCILED:
        return get_bank_statement_line(db, line.id)
    entry = db.scalar(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == journal_entry_id)
    )
    if entry is None:
        raise ValueError(f"Unknown journal entry id: {journal_entry_id}")
    existing_match = db.scalar(
        select(BankStatementLine).where(
            BankStatementLine.journal_entry_id == journal_entry_id,
            BankStatementLine.id != line_id,
        )
    )
    if existing_match is not None:
        raise ValueError("This journal entry is already linked to another bank statement line.")
    bank_amount = _journal_entry_bank_amount(entry, line.bank_account_id)
    if bank_amount != line.amount:
        raise ValueError("Journal entry bank movement must match the statement line amount.")
    line.status = BankStatementLineStatus.RECONCILED
    line.journal_entry_id = journal_entry_id
    line.reconciled_at = datetime.now(UTC)
    _record_audit_event(
        db,
        entity_type="bank_statement_line",
        entity_id=line.id,
        action="reconciled",
        summary=f"Bank statement line {line.id} reconciled to journal entry {journal_entry_id}.",
        details={
            "journal_entry_id": journal_entry_id,
            "bank_account_id": line.bank_account_id,
            "amount": line.amount,
        },
    )
    db.commit()
    return get_bank_statement_line(db, line.id)


def unreconcile_bank_statement_line(db: Session, line_id: int) -> BankStatementLine:
    line = db.get(BankStatementLine, line_id)
    if line is None:
        raise ValueError(f"Unknown bank statement line id: {line_id}")
    if line.status != BankStatementLineStatus.RECONCILED:
        return get_bank_statement_line(db, line.id)
    line.status = BankStatementLineStatus.UNMATCHED
    line.journal_entry_id = None
    line.reconciled_at = None
    _record_audit_event(
        db,
        entity_type="bank_statement_line",
        entity_id=line.id,
        action="unreconciled",
        summary=f"Bank statement line {line.id} was unreconciled.",
        details={"bank_account_id": line.bank_account_id, "amount": line.amount},
    )
    db.commit()
    return get_bank_statement_line(db, line.id)


def bank_reconciliation_summary(db: Session, bank_account_id: int, limit: int = 100) -> BankReconciliationSummary:
    bank_account = _get_account(db, bank_account_id)
    if bank_account.type != AccountType.ASSET:
        raise ValueError("Bank reconciliation account must be an asset account.")
    lines = list_bank_statement_lines(db, bank_account_id=bank_account_id, limit=limit)
    reconciled_lines = [line for line in lines if line.status == BankStatementLineStatus.RECONCILED]
    unmatched_lines = [line for line in lines if line.status == BankStatementLineStatus.UNMATCHED]
    statement_total = sum((line.amount for line in lines), Decimal("0.00")).quantize(Decimal("0.01"))
    reconciled_total = sum((line.amount for line in reconciled_lines), Decimal("0.00")).quantize(Decimal("0.01"))
    return BankReconciliationSummary(
        bank_account=AccountRead.model_validate(bank_account).model_copy(update={"balance": Decimal("0.00")}),
        statement_total=statement_total,
        reconciled_total=reconciled_total,
        unreconciled_total=(statement_total - reconciled_total).quantize(Decimal("0.01")),
        unmatched_count=len(unmatched_lines),
        reconciled_count=len(reconciled_lines),
        lines=lines,
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


def _generate_supplier_bill_number(db: Session, bill_date) -> str:
    prefix = f"BILL-{bill_date:%Y%m}"
    count = db.scalar(select(func.count()).select_from(SupplierBill).where(SupplierBill.bill_number.like(f"{prefix}-%"))) or 0
    return f"{prefix}-{count + 1:04d}"


def _validate_vendor_for_supplier_bill(vendor: Contact) -> None:
    if vendor.type not in {ContactType.VENDOR, ContactType.BOTH}:
        raise ValueError("Supplier bills can only be assigned to vendor contacts.")


def _validate_supplier_bill_lines(db: Session, payload: SupplierBillCreate) -> None:
    for line in payload.lines:
        account = _get_account(db, line.expense_account_id)
        if account.type not in {AccountType.EXPENSE, AccountType.ASSET}:
            raise ValueError("Supplier bill lines must use expense or asset accounts.")


def supplier_bill_query():
    return select(SupplierBill).options(
        selectinload(SupplierBill.vendor),
        selectinload(SupplierBill.purchase_order)
        .selectinload(PurchaseOrder.lines)
        .selectinload(PurchaseOrderLine.expense_account),
        selectinload(SupplierBill.purchase_order).selectinload(PurchaseOrder.vendor),
        selectinload(SupplierBill.project).selectinload(Project.client),
        selectinload(SupplierBill.lines).selectinload(SupplierBillLine.expense_account),
        selectinload(SupplierBill.allocations).selectinload(SupplierPaymentAllocation.payment),
    )


def get_supplier_bill(db: Session, bill_id: int) -> SupplierBill:
    bill = db.scalar(supplier_bill_query().where(SupplierBill.id == bill_id))
    if bill is None:
        raise ValueError(f"Unknown supplier bill id: {bill_id}")
    return bill


def list_supplier_bills(db: Session, limit: int = 50) -> list[SupplierBill]:
    return list(
        db.scalars(
            supplier_bill_query().order_by(
                SupplierBill.bill_date.desc(),
                SupplierBill.id.desc(),
            ).limit(limit)
        ).all()
    )


def create_supplier_bill(db: Session, payload: SupplierBillCreate) -> SupplierBill:
    vendor = db.get(Contact, payload.vendor_id)
    if vendor is None:
        raise ValueError(f"Unknown vendor id: {payload.vendor_id}")
    _validate_vendor_for_supplier_bill(vendor)
    _validate_supplier_bill_lines(db, payload)

    if payload.purchase_order_id is not None:
        purchase_order = db.get(PurchaseOrder, payload.purchase_order_id)
        if purchase_order is None:
            raise ValueError(f"Unknown purchase order id: {payload.purchase_order_id}")
        if purchase_order.vendor_id != payload.vendor_id:
            raise ValueError("Supplier bill vendor must match the linked purchase order vendor.")
        if purchase_order.status == PurchaseOrderStatus.CANCELLED:
            raise ValueError("Cancelled purchase orders cannot be billed.")

    if payload.project_id is not None:
        project = db.get(Project, payload.project_id)
        if project is None:
            raise ValueError(f"Unknown project id: {payload.project_id}")
        if project.status == ProjectStatus.CANCELLED:
            raise ValueError("Cancelled projects cannot be linked to new activity.")

    bill = SupplierBill(
        bill_number=payload.bill_number or _generate_supplier_bill_number(db, payload.bill_date),
        status=payload.status,
        vendor_id=payload.vendor_id,
        purchase_order_id=payload.purchase_order_id,
        project_id=payload.project_id,
        bill_date=payload.bill_date,
        due_date=payload.due_date,
        currency=payload.currency,
        payment_terms=payload.payment_terms,
        reference=payload.reference,
        notes=payload.notes,
    )
    for line in payload.lines:
        bill.lines.append(SupplierBillLine(**line.model_dump()))
    db.add(bill)
    db.flush()

    if bill.status == SupplierBillStatus.POSTED:
        _post_supplier_bill(db, bill)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("Supplier bill number must be unique.") from exc
    return get_supplier_bill(db, bill.id)


def _post_supplier_bill(db: Session, bill: SupplierBill) -> None:
    if bill.status == SupplierBillStatus.VOIDED:
        raise ValueError("Voided supplier bills cannot be posted.")
    if bill.journal_entry_id is not None:
        return
    if not bill.lines:
        raise ValueError("Supplier bill must have at least one line.")

    ap_account = _get_account_by_code(db, "2000")
    lines = []
    for bill_line in bill.lines:
        lines.append(
            {
                "account_id": bill_line.expense_account_id,
                "debit": bill_line.line_subtotal,
                "description": bill_line.description,
            }
        )
    if bill.tax_total > 0:
        gst_input_account = _get_account_by_code(db, "2210")
        lines.append(
            {
                "account_id": gst_input_account.id,
                "debit": bill.tax_total,
                "description": f"Input tax for {bill.bill_number}",
            }
        )
    lines.append(
        {
            "account_id": ap_account.id,
            "credit": bill.total,
            "description": f"Accounts payable for {bill.bill_number}",
        }
    )

    entry = create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=bill.bill_date,
            memo=f"Supplier bill {bill.bill_number}",
            reference=bill.reference or bill.bill_number,
            lines=lines,
        ),
        commit=False,
    )
    bill._allow_accounting_post_mutation = True
    bill.journal_entry_id = entry.id
    bill.status = SupplierBillStatus.POSTED
    bill.posted_at = datetime.now(UTC)
    if bill.purchase_order is not None and bill.purchase_order.status not in {PurchaseOrderStatus.CLOSED, PurchaseOrderStatus.CANCELLED}:
        bill.purchase_order.status = PurchaseOrderStatus.BILLED
    _record_audit_event(
        db,
        entity_type="supplier_bill",
        entity_id=bill.id,
        action="posted",
        summary=f"Supplier bill {bill.bill_number} posted to Accounts Payable.",
        details={
            "journal_entry_id": entry.id,
            "vendor_id": bill.vendor_id,
            "total": bill.total,
        },
    )


def post_supplier_bill(db: Session, bill_id: int) -> SupplierBill:
    bill = db.scalar(
        select(SupplierBill)
        .options(
            selectinload(SupplierBill.lines),
            selectinload(SupplierBill.purchase_order),
        )
        .where(SupplierBill.id == bill_id)
    )
    if bill is None:
        raise ValueError(f"Unknown supplier bill id: {bill_id}")
    if bill.status == SupplierBillStatus.POSTED:
        return get_supplier_bill(db, bill.id)
    _ensure_approval_allows_action(db, "supplier_bill", bill.id)
    _post_supplier_bill(db, bill)
    db.commit()
    return get_supplier_bill(db, bill.id)


def _generate_supplier_payment_number(db: Session, payment_date) -> str:
    prefix = f"PAY-{payment_date:%Y%m}"
    count = db.scalar(select(func.count()).select_from(SupplierPayment).where(SupplierPayment.payment_number.like(f"{prefix}-%"))) or 0
    return f"{prefix}-{count + 1:04d}"


def supplier_payment_query():
    return select(SupplierPayment).options(
        selectinload(SupplierPayment.vendor),
        selectinload(SupplierPayment.bank_account),
        selectinload(SupplierPayment.allocations)
        .selectinload(SupplierPaymentAllocation.bill)
        .selectinload(SupplierBill.vendor),
        selectinload(SupplierPayment.allocations)
        .selectinload(SupplierPaymentAllocation.bill)
        .selectinload(SupplierBill.lines)
        .selectinload(SupplierBillLine.expense_account),
        selectinload(SupplierPayment.allocations)
        .selectinload(SupplierPaymentAllocation.bill)
        .selectinload(SupplierBill.allocations)
        .selectinload(SupplierPaymentAllocation.payment),
    )


def get_supplier_payment(db: Session, payment_id: int) -> SupplierPayment:
    payment = db.scalar(supplier_payment_query().where(SupplierPayment.id == payment_id))
    if payment is None:
        raise ValueError(f"Unknown supplier payment id: {payment_id}")
    return payment


def list_supplier_payments(db: Session, limit: int = 50) -> list[SupplierPayment]:
    return list(
        db.scalars(
            supplier_payment_query().order_by(
                SupplierPayment.payment_date.desc(),
                SupplierPayment.id.desc(),
            ).limit(limit)
        ).all()
    )


def _post_supplier_payment(db: Session, payment: SupplierPayment) -> None:
    if payment.status == SupplierPaymentStatus.VOIDED:
        raise ValueError("Voided supplier payments cannot be posted.")
    if payment.journal_entry_id is not None:
        return
    ap_account = _get_account_by_code(db, "2000")
    entry = create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=payment.payment_date,
            memo=f"Supplier payment {payment.payment_number}",
            reference=payment.reference or payment.payment_number,
            lines=[
                {
                    "account_id": ap_account.id,
                    "debit": payment.amount,
                    "description": f"Payment {payment.payment_number}",
                },
                {
                    "account_id": payment.bank_account_id,
                    "credit": payment.amount,
                    "description": f"Payment {payment.payment_number}",
                },
            ],
        ),
        commit=False,
    )
    payment._allow_accounting_post_mutation = True
    payment.journal_entry_id = entry.id
    payment.status = SupplierPaymentStatus.POSTED
    payment.posted_at = datetime.now(UTC)
    _record_audit_event(
        db,
        entity_type="supplier_payment",
        entity_id=payment.id,
        action="posted",
        summary=f"Supplier payment {payment.payment_number} posted against Accounts Payable.",
        details={
            "journal_entry_id": entry.id,
            "vendor_id": payment.vendor_id,
            "amount": payment.amount,
        },
    )


def create_supplier_payment(db: Session, payload: SupplierPaymentCreate) -> SupplierPayment:
    if payload.status not in {SupplierPaymentStatus.DRAFT, SupplierPaymentStatus.POSTED}:
        raise ValueError("Supplier payments can only be created as draft or posted.")
    vendor = db.get(Contact, payload.vendor_id)
    if vendor is None:
        raise ValueError(f"Unknown vendor id: {payload.vendor_id}")
    _validate_vendor_for_supplier_bill(vendor)
    bank_account = _get_account(db, payload.bank_account_id)
    if bank_account.type != AccountType.ASSET:
        raise ValueError("Supplier payments must credit a cash or bank asset account.")

    bills_by_id: dict[int, SupplierBill] = {}
    allocation_totals_by_bill: dict[int, Decimal] = {}
    for allocation_payload in payload.allocations:
        bill = get_supplier_bill(db, allocation_payload.bill_id)
        if bill.vendor_id != payload.vendor_id:
            raise ValueError("Payment allocations must use supplier bills for the same vendor.")
        if bill.status != SupplierBillStatus.POSTED:
            raise ValueError("Supplier payments can only be allocated to posted supplier bills.")
        allocation_total = allocation_totals_by_bill.get(bill.id, Decimal("0.00")) + allocation_payload.amount
        if allocation_total > bill.amount_due:
            raise ValueError(f"Allocation exceeds amount due for supplier bill {bill.bill_number}.")
        bills_by_id[bill.id] = bill
        allocation_totals_by_bill[bill.id] = allocation_total

    payment = SupplierPayment(
        payment_number=payload.payment_number or _generate_supplier_payment_number(db, payload.payment_date),
        status=payload.status,
        vendor_id=payload.vendor_id,
        payment_date=payload.payment_date,
        currency=payload.currency,
        amount=payload.amount,
        bank_account_id=payload.bank_account_id,
        reference=payload.reference,
        notes=payload.notes,
    )
    for allocation_payload in payload.allocations:
        payment.allocations.append(
            SupplierPaymentAllocation(
                bill=bills_by_id[allocation_payload.bill_id],
                amount=allocation_payload.amount,
            )
        )
    db.add(payment)
    db.flush()
    if payment.status == SupplierPaymentStatus.POSTED:
        _post_supplier_payment(db, payment)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("Supplier payment number must be unique.") from exc
    return get_supplier_payment(db, payment.id)


def post_supplier_payment(db: Session, payment_id: int) -> SupplierPayment:
    payment = db.scalar(
        select(SupplierPayment)
        .options(selectinload(SupplierPayment.allocations).selectinload(SupplierPaymentAllocation.bill))
        .where(SupplierPayment.id == payment_id)
    )
    if payment is None:
        raise ValueError(f"Unknown supplier payment id: {payment_id}")
    if payment.status == SupplierPaymentStatus.POSTED:
        return get_supplier_payment(db, payment.id)
    _ensure_approval_allows_action(db, "supplier_payment", payment.id)
    for allocation in payment.allocations:
        if allocation.amount > allocation.bill.amount_due:
            raise ValueError(f"Allocation exceeds amount due for supplier bill {allocation.bill.bill_number}.")
    _post_supplier_payment(db, payment)
    db.commit()
    return get_supplier_payment(db, payment.id)


def _generate_sales_order_number(db: Session, received_date) -> str:
    prefix = f"SO-{received_date:%Y%m}"
    count = db.scalar(select(func.count()).select_from(SalesOrder).where(SalesOrder.order_number.like(f"{prefix}-%"))) or 0
    return f"{prefix}-{count + 1:04d}"


def _validate_customer_for_sales_order(customer: Contact) -> None:
    if customer.type not in {ContactType.CUSTOMER, ContactType.BOTH}:
        raise ValueError("Client purchase orders can only be assigned to customer contacts.")


def _validate_sales_order_lines(db: Session, payload: SalesOrderCreate) -> None:
    for line in payload.lines:
        account = _get_account(db, line.revenue_account_id)
        if account.type != AccountType.REVENUE:
            raise ValueError("Sales order lines must use revenue accounts.")


def _sales_order_total(payload: SalesOrderCreate) -> Decimal:
    subtotal = sum((line.quantity * line.unit_price for line in payload.lines), Decimal("0.00"))
    tax_total = sum((line.tax_amount for line in payload.lines), Decimal("0.00"))
    return (subtotal + tax_total).quantize(Decimal("0.01"))


def _deposit_amount_for_order(payload: SalesOrderCreate) -> Decimal:
    if not payload.deposit_required:
        return Decimal("0.00")
    total = _sales_order_total(payload)
    deposit_rate = payload.deposit_rate or Decimal("0.1000")
    deposit_amount = payload.deposit_amount
    if deposit_amount is None or deposit_amount == 0:
        deposit_amount = (total * deposit_rate).quantize(Decimal("0.01"))
    if deposit_amount <= 0:
        raise ValueError("Required deposits need a deposit amount greater than zero.")
    if deposit_amount > total:
        raise ValueError("Deposit amount cannot exceed sales order total.")
    return deposit_amount


def _post_sales_order_deposit(db: Session, sales_order: SalesOrder) -> None:
    if not sales_order.deposit_required or sales_order.deposit_status != DepositStatus.PAID:
        return
    if sales_order.deposit_transaction_id is not None:
        return
    bank_account = _get_account_by_code(db, "1010")
    deferred_revenue = _get_account_by_code(db, "2150")
    transaction = OperationalTransaction(
        kind=TransactionKind.DEPOSIT,
        status=TransactionStatus.POSTED,
        transaction_date=sales_order.deposit_due_date or sales_order.received_date,
        description=f"Deposit received for {sales_order.order_number}",
        reference=sales_order.order_number,
        amount=sales_order.deposit_amount,
        contact_id=sales_order.customer_id,
        project_id=sales_order.project_id,
        debit_account_id=bank_account.id,
        credit_account_id=deferred_revenue.id,
    )
    db.add(transaction)
    db.flush()
    _post_operational_transaction(db, transaction)
    sales_order.deposit_transaction_id = transaction.id


def sales_order_query():
    return select(SalesOrder).options(
        selectinload(SalesOrder.customer),
        selectinload(SalesOrder.project).selectinload(Project.client),
        selectinload(SalesOrder.lines).selectinload(SalesOrderLine.revenue_account),
        selectinload(SalesOrder.invoices).selectinload(SalesInvoice.lines),
        selectinload(SalesOrder.invoices)
        .selectinload(SalesInvoice.allocations)
        .selectinload(CustomerReceiptAllocation.receipt),
    )


def get_sales_order(db: Session, sales_order_id: int) -> SalesOrder:
    sales_order = db.scalar(sales_order_query().where(SalesOrder.id == sales_order_id))
    if sales_order is None:
        raise ValueError(f"Unknown sales order id: {sales_order_id}")
    return sales_order


def list_sales_orders(db: Session, limit: int = 50) -> list[SalesOrder]:
    return list(
        db.scalars(
            sales_order_query().order_by(
                SalesOrder.received_date.desc(),
                SalesOrder.id.desc(),
            ).limit(limit)
        ).all()
    )


def create_sales_order(db: Session, payload: SalesOrderCreate) -> SalesOrder:
    customer = db.get(Contact, payload.customer_id)
    if customer is None:
        raise ValueError(f"Unknown customer id: {payload.customer_id}")
    _validate_customer_for_sales_order(customer)
    _validate_project_for_customer(db, payload.project_id, payload.customer_id)
    _validate_sales_order_lines(db, payload)
    deposit_amount = _deposit_amount_for_order(payload)
    deposit_rate = payload.deposit_rate or (Decimal("0.1000") if payload.deposit_required else Decimal("0.0000"))
    deposit_status = payload.deposit_status
    if payload.deposit_required and deposit_status == DepositStatus.NOT_REQUESTED:
        deposit_status = DepositStatus.REQUESTED

    order_number = payload.order_number or _generate_sales_order_number(db, payload.received_date)
    client_po_number = payload.client_po_number.strip() if payload.client_po_number else ""
    sales_order = SalesOrder(
        order_number=order_number,
        client_po_number=client_po_number or f"NO-PO-{order_number}",
        status=payload.status,
        customer_id=payload.customer_id,
        project_id=payload.project_id,
        received_date=payload.received_date,
        expected_delivery_date=payload.expected_delivery_date,
        currency=payload.currency,
        payment_terms=payload.payment_terms,
        deposit_required=payload.deposit_required,
        deposit_rate=deposit_rate,
        deposit_amount=deposit_amount,
        deposit_due_date=payload.deposit_due_date,
        deposit_status=deposit_status,
        notes=payload.notes,
        delivery_instructions=payload.delivery_instructions,
    )
    if sales_order.status == SalesOrderStatus.ACCEPTED:
        sales_order.accepted_at = datetime.now(UTC)
    for line in payload.lines:
        sales_order.lines.append(SalesOrderLine(**line.model_dump()))
    db.add(sales_order)
    db.flush()
    _post_sales_order_deposit(db, sales_order)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("Sales order number must be unique.") from exc
    return get_sales_order(db, sales_order.id)


def post_unposted_paid_sales_order_deposits(db: Session) -> int:
    sales_orders = db.scalars(
        select(SalesOrder).where(
            SalesOrder.deposit_required.is_(True),
            SalesOrder.deposit_status == DepositStatus.PAID,
            SalesOrder.deposit_transaction_id.is_(None),
        )
    ).all()
    for sales_order in sales_orders:
        _post_sales_order_deposit(db, sales_order)
    if sales_orders:
        db.commit()
    return len(sales_orders)


def accept_sales_order(db: Session, sales_order_id: int) -> SalesOrder:
    sales_order = db.get(SalesOrder, sales_order_id)
    if sales_order is None:
        raise ValueError(f"Unknown sales order id: {sales_order_id}")
    if sales_order.status == SalesOrderStatus.ACCEPTED:
        return get_sales_order(db, sales_order.id)
    if sales_order.status not in {SalesOrderStatus.DRAFT, SalesOrderStatus.RECEIVED}:
        raise ValueError("Only draft or received client purchase orders can be accepted.")
    sales_order.status = SalesOrderStatus.ACCEPTED
    sales_order.accepted_at = datetime.now(UTC)
    db.commit()
    return get_sales_order(db, sales_order.id)


def cancel_sales_order(db: Session, sales_order_id: int) -> SalesOrder:
    sales_order = db.get(SalesOrder, sales_order_id)
    if sales_order is None:
        raise ValueError(f"Unknown sales order id: {sales_order_id}")
    if sales_order.status in {SalesOrderStatus.CLOSED, SalesOrderStatus.CANCELLED}:
        return get_sales_order(db, sales_order.id)
    if sales_order.status in {SalesOrderStatus.INVOICED, SalesOrderStatus.FULFILLED}:
        raise ValueError("Invoiced or fulfilled sales orders cannot be cancelled here.")
    sales_order.status = SalesOrderStatus.CANCELLED
    sales_order.cancelled_at = datetime.now(UTC)
    db.commit()
    return get_sales_order(db, sales_order.id)


def _generate_invoice_number(db: Session, issue_date: date) -> str:
    prefix = f"INV-{issue_date:%Y%m}"
    count = db.scalar(select(func.count()).select_from(SalesInvoice).where(SalesInvoice.invoice_number.like(f"{prefix}-%"))) or 0
    return f"{prefix}-{count + 1:04d}"


def _generate_receipt_number(
    db: Session,
    receipt_date: date,
    invoice_number: str | None = None,
    invoice_id: int | None = None,
) -> str:
    if invoice_number:
        prefix = f"{invoice_number}-R{receipt_date:%Y%m%d}"
        if invoice_id is not None:
            count = (
                db.scalar(
                    select(func.count())
                    .select_from(CustomerReceiptAllocation)
                    .join(CustomerReceipt, CustomerReceipt.id == CustomerReceiptAllocation.receipt_id)
                    .where(CustomerReceiptAllocation.invoice_id == invoice_id)
                    .where(CustomerReceipt.receipt_date == receipt_date)
                )
                or 0
            )
        else:
            count = db.scalar(select(func.count()).select_from(CustomerReceipt).where(CustomerReceipt.receipt_number.like(f"{prefix}-%"))) or 0
        return f"{prefix}-{count + 1:02d}"
    prefix = f"REC-{receipt_date:%Y%m}"
    count = db.scalar(select(func.count()).select_from(CustomerReceipt).where(CustomerReceipt.receipt_number.like(f"{prefix}-%"))) or 0
    return f"{prefix}-{count + 1:04d}"


def _validate_customer_contact(customer: Contact) -> None:
    if customer.type not in {ContactType.CUSTOMER, ContactType.BOTH}:
        raise ValueError("Invoices and customer receipts can only be assigned to customer contacts.")


def _validate_sales_invoice_lines(db: Session, payload: SalesInvoiceCreate) -> None:
    for line in payload.lines:
        account = _get_account(db, line.revenue_account_id)
        if account.type != AccountType.REVENUE:
            raise ValueError("Sales invoice lines must use revenue accounts.")


def _single_open_sales_order_for_customer(db: Session, customer_id: int) -> SalesOrder | None:
    sales_orders = db.scalars(
        sales_order_query()
        .where(SalesOrder.customer_id == customer_id)
        .where(SalesOrder.status.notin_([SalesOrderStatus.CLOSED, SalesOrderStatus.CANCELLED]))
    ).all()
    candidates = [sales_order for sales_order in sales_orders if sales_order.unbilled_total > 0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def sales_invoice_query():
    return select(SalesInvoice).options(
        selectinload(SalesInvoice.customer),
        selectinload(SalesInvoice.project).selectinload(Project.client),
        selectinload(SalesInvoice.sales_order).selectinload(SalesOrder.customer),
        selectinload(SalesInvoice.sales_order).selectinload(SalesOrder.lines).selectinload(SalesOrderLine.revenue_account),
        selectinload(SalesInvoice.lines).selectinload(SalesInvoiceLine.revenue_account),
        selectinload(SalesInvoice.allocations).selectinload(CustomerReceiptAllocation.receipt),
    )


def get_sales_invoice(db: Session, invoice_id: int) -> SalesInvoice:
    invoice = db.scalar(sales_invoice_query().where(SalesInvoice.id == invoice_id))
    if invoice is None:
        raise ValueError(f"Unknown sales invoice id: {invoice_id}")
    return invoice


def list_sales_invoices(db: Session, limit: int = 50) -> list[SalesInvoice]:
    return list(
        db.scalars(
            sales_invoice_query().order_by(
                SalesInvoice.issue_date.desc(),
                SalesInvoice.id.desc(),
            ).limit(limit)
        ).all()
    )


def _post_sales_invoice(db: Session, invoice: SalesInvoice) -> None:
    if invoice.journal_entry_id is not None:
        return
    ar_account = _get_account_by_code(db, "1100")
    gst_output_account = _get_account_by_code(db, "2200")
    lines = [
        {
            "account_id": ar_account.id,
            "debit": invoice.total,
            "description": f"Invoice {invoice.invoice_number}",
        }
    ]
    revenue_by_account: dict[int, Decimal] = {}
    for line in invoice.lines:
        line_revenue = (line.quantity * line.unit_price).quantize(Decimal("0.01"))
        revenue_by_account[line.revenue_account_id] = revenue_by_account.get(line.revenue_account_id, Decimal("0.00")) + line_revenue
    for account_id, amount in revenue_by_account.items():
        if amount > 0:
            lines.append(
                {
                    "account_id": account_id,
                    "credit": amount.quantize(Decimal("0.01")),
                    "description": f"Revenue for {invoice.invoice_number}",
                }
            )
    if invoice.tax_total > 0:
        lines.append(
            {
                "account_id": gst_output_account.id,
                "credit": invoice.tax_total,
                "description": f"GST output tax for {invoice.invoice_number}",
            }
        )
    entry = create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=invoice.issue_date,
            memo=f"Sales invoice {invoice.invoice_number}",
            reference=invoice.invoice_number,
            lines=lines,
        ),
        commit=False,
    )
    invoice.journal_entry_id = entry.id
    invoice.status = SalesInvoiceStatus.ISSUED
    invoice.issued_at = datetime.now(UTC)
    if invoice.sales_order is not None and invoice.sales_order.status not in {SalesOrderStatus.CLOSED, SalesOrderStatus.CANCELLED}:
        _refresh_sales_order_invoice_status(invoice.sales_order)


def _refresh_sales_order_invoice_status(sales_order: SalesOrder) -> None:
    if sales_order.status in {SalesOrderStatus.CLOSED, SalesOrderStatus.CANCELLED}:
        return
    if sales_order.invoiced_total <= 0:
        return
    if sales_order.invoiced_total >= sales_order.total:
        sales_order.status = SalesOrderStatus.INVOICED
    else:
        sales_order.status = SalesOrderStatus.PARTIALLY_INVOICED


def _refresh_invoice_payment_status(invoice: SalesInvoice) -> None:
    if invoice.status in {SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.VOIDED}:
        return
    if invoice.amount_due <= 0:
        invoice.status = SalesInvoiceStatus.PAID
    elif invoice.amount_paid > 0:
        invoice.status = SalesInvoiceStatus.PARTIALLY_PAID
    else:
        invoice.status = SalesInvoiceStatus.ISSUED


def create_sales_invoice(db: Session, payload: SalesInvoiceCreate) -> SalesInvoice:
    if payload.status not in {SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.ISSUED}:
        raise ValueError("Sales invoices can only be created as draft or issued.")
    customer = db.get(Contact, payload.customer_id)
    if customer is None:
        raise ValueError(f"Unknown customer id: {payload.customer_id}")
    _validate_customer_contact(customer)
    sales_order = None
    if payload.sales_order_id is not None:
        sales_order = db.get(SalesOrder, payload.sales_order_id)
        if sales_order is None:
            raise ValueError(f"Unknown sales order id: {payload.sales_order_id}")
        if sales_order.customer_id != payload.customer_id:
            raise ValueError("Sales invoice customer must match the linked sales order customer.")
        if payload.project_id is not None and sales_order.project_id is not None and payload.project_id != sales_order.project_id:
            raise ValueError("Sales invoice project must match the linked sales booking project.")
    else:
        sales_order = _single_open_sales_order_for_customer(db, payload.customer_id)
    project_id = payload.project_id if payload.project_id is not None else sales_order.project_id if sales_order is not None else None
    _validate_project_for_customer(db, project_id, payload.customer_id)
    _validate_sales_invoice_lines(db, payload)

    invoice = SalesInvoice(
        invoice_number=payload.invoice_number or _generate_invoice_number(db, payload.issue_date),
        status=payload.status,
        customer_id=payload.customer_id,
        sales_order_id=sales_order.id if sales_order is not None else None,
        project_id=project_id,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        currency=payload.currency,
        payment_terms=payload.payment_terms,
        notes=payload.notes,
    )
    if sales_order is not None:
        invoice.sales_order = sales_order
    for line in payload.lines:
        invoice.lines.append(SalesInvoiceLine(**line.model_dump()))
    db.add(invoice)
    db.flush()
    if invoice.status == SalesInvoiceStatus.ISSUED:
        _post_sales_invoice(db, invoice)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("Invoice number must be unique.") from exc
    return get_sales_invoice(db, invoice.id)


def issue_sales_invoice(db: Session, invoice_id: int) -> SalesInvoice:
    invoice = db.scalar(
        select(SalesInvoice)
        .options(selectinload(SalesInvoice.lines), selectinload(SalesInvoice.sales_order))
        .where(SalesInvoice.id == invoice_id)
    )
    if invoice is None:
        raise ValueError(f"Unknown sales invoice id: {invoice_id}")
    if invoice.status == SalesInvoiceStatus.VOIDED:
        raise ValueError("Voided sales invoices cannot be issued.")
    _post_sales_invoice(db, invoice)
    db.commit()
    return get_sales_invoice(db, invoice.id)


def link_sales_invoice_to_sales_order(db: Session, invoice_id: int, sales_order_id: int) -> SalesInvoice:
    invoice = db.scalar(
        sales_invoice_query()
        .where(SalesInvoice.id == invoice_id)
    )
    if invoice is None:
        raise ValueError(f"Unknown sales invoice id: {invoice_id}")
    if invoice.status in {SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.VOIDED}:
        raise ValueError("Only issued invoices can be linked to a sales booking.")
    if invoice.sales_order_id == sales_order_id:
        return invoice
    if invoice.sales_order_id is not None:
        raise ValueError("Invoice is already linked to a sales booking.")

    sales_order = get_sales_order(db, sales_order_id)
    if sales_order.customer_id != invoice.customer_id:
        raise ValueError("Sales invoice customer must match the linked sales booking customer.")
    if sales_order.status in {SalesOrderStatus.CLOSED, SalesOrderStatus.CANCELLED}:
        raise ValueError("Closed or cancelled sales bookings cannot be linked.")
    if invoice.total > sales_order.unbilled_total:
        raise ValueError("Invoice total exceeds the sales booking unbilled amount.")
    if invoice.project_id is not None and sales_order.project_id is not None and invoice.project_id != sales_order.project_id:
        raise ValueError("Sales invoice project must match the linked sales booking project.")

    invoice.sales_order_id = sales_order.id
    invoice.sales_order = sales_order
    if invoice.project_id is None:
        invoice.project_id = sales_order.project_id
    _refresh_sales_order_invoice_status(sales_order)
    db.commit()
    return get_sales_invoice(db, invoice.id)


def customer_receipt_query():
    return select(CustomerReceipt).options(
        selectinload(CustomerReceipt.customer),
        selectinload(CustomerReceipt.bank_account),
        selectinload(CustomerReceipt.allocations)
        .selectinload(CustomerReceiptAllocation.invoice)
        .selectinload(SalesInvoice.customer),
        selectinload(CustomerReceipt.allocations)
        .selectinload(CustomerReceiptAllocation.invoice)
        .selectinload(SalesInvoice.lines)
        .selectinload(SalesInvoiceLine.revenue_account),
        selectinload(CustomerReceipt.allocations)
        .selectinload(CustomerReceiptAllocation.invoice)
        .selectinload(SalesInvoice.allocations)
        .selectinload(CustomerReceiptAllocation.receipt),
    )


def get_customer_receipt(db: Session, receipt_id: int) -> CustomerReceipt:
    receipt = db.scalar(customer_receipt_query().where(CustomerReceipt.id == receipt_id))
    if receipt is None:
        raise ValueError(f"Unknown customer receipt id: {receipt_id}")
    return receipt


def list_customer_receipts(db: Session, limit: int = 50) -> list[CustomerReceipt]:
    return list(
        db.scalars(
            customer_receipt_query().order_by(
                CustomerReceipt.receipt_date.desc(),
                CustomerReceipt.id.desc(),
            ).limit(limit)
        ).all()
    )


def _post_customer_receipt(db: Session, receipt: CustomerReceipt) -> None:
    if receipt.journal_entry_id is not None:
        return
    ar_account = _get_account_by_code(db, "1100")
    entry = create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=receipt.receipt_date,
            memo=f"Customer receipt {receipt.receipt_number}",
            reference=receipt.reference or receipt.receipt_number,
            lines=[
                {
                    "account_id": receipt.bank_account_id,
                    "debit": receipt.amount,
                    "description": f"Receipt {receipt.receipt_number}",
                },
                {
                    "account_id": ar_account.id,
                    "credit": receipt.amount,
                    "description": f"Receipt {receipt.receipt_number}",
                },
            ],
        ),
        commit=False,
    )
    receipt.journal_entry_id = entry.id
    receipt.status = CustomerReceiptStatus.POSTED
    receipt.posted_at = datetime.now(UTC)


def create_customer_receipt(db: Session, payload: CustomerReceiptCreate) -> CustomerReceipt:
    if payload.status not in {CustomerReceiptStatus.DRAFT, CustomerReceiptStatus.POSTED}:
        raise ValueError("Customer receipts can only be created as draft or posted.")
    customer = db.get(Contact, payload.customer_id)
    if customer is None:
        raise ValueError(f"Unknown customer id: {payload.customer_id}")
    _validate_customer_contact(customer)
    bank_account = _get_account(db, payload.bank_account_id)
    if bank_account.type != AccountType.ASSET:
        raise ValueError("Customer receipts must debit a cash or bank asset account.")

    invoices_by_id: dict[int, SalesInvoice] = {}
    allocation_totals_by_invoice: dict[int, Decimal] = {}
    for allocation_payload in payload.allocations:
        invoice = get_sales_invoice(db, allocation_payload.invoice_id)
        if invoice.customer_id != payload.customer_id:
            raise ValueError("Receipt allocations must use invoices for the same customer.")
        if invoice.status in {SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.VOIDED}:
            raise ValueError("Receipts can only be allocated to issued invoices.")
        allocation_total = allocation_totals_by_invoice.get(invoice.id, Decimal("0.00")) + allocation_payload.amount
        if allocation_total > invoice.amount_due:
            raise ValueError(f"Allocation exceeds amount due for invoice {invoice.invoice_number}.")
        invoices_by_id[invoice.id] = invoice
        allocation_totals_by_invoice[invoice.id] = allocation_total

    first_invoice_id = payload.allocations[0].invoice_id if payload.allocations else None
    first_invoice_number = invoices_by_id[first_invoice_id].invoice_number if first_invoice_id in invoices_by_id else None
    receipt = CustomerReceipt(
        receipt_number=payload.receipt_number or _generate_receipt_number(db, payload.receipt_date, first_invoice_number, first_invoice_id),
        status=payload.status,
        customer_id=payload.customer_id,
        receipt_date=payload.receipt_date,
        currency=payload.currency,
        amount=payload.amount,
        bank_account_id=payload.bank_account_id,
        reference=payload.reference,
        notes=payload.notes,
    )
    for allocation_payload in payload.allocations:
        invoice = invoices_by_id[allocation_payload.invoice_id]
        receipt.allocations.append(
            CustomerReceiptAllocation(
                invoice=invoice,
                amount=allocation_payload.amount,
            )
        )
    db.add(receipt)
    db.flush()
    if receipt.status == CustomerReceiptStatus.POSTED:
        _post_customer_receipt(db, receipt)
        for invoice in invoices_by_id.values():
            _refresh_invoice_payment_status(invoice)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("Receipt number must be unique.") from exc
    return get_customer_receipt(db, receipt.id)


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
    payroll._allow_accounting_post_mutation = True
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


def client_history(db: Session) -> ClientHistoryReport:
    sales_orders = list_sales_orders(db, limit=1000)
    sales_invoices = list_sales_invoices(db, limit=1000)
    customer_receipts = list_customer_receipts(db, limit=1000)
    customers = [
        contact
        for contact in list_contacts(db)
        if contact.type in {ContactType.CUSTOMER, ContactType.BOTH}
    ]

    entries: list[ClientHistoryEntry] = []
    for customer in customers:
        customer_orders = [order for order in sales_orders if order.customer_id == customer.id]
        customer_invoices = [invoice for invoice in sales_invoices if invoice.customer_id == customer.id]
        customer_receipt_rows = [receipt for receipt in customer_receipts if receipt.customer_id == customer.id]
        if not customer_orders and not customer_invoices and not customer_receipt_rows:
            continue

        ordered_total = sum((order.total for order in customer_orders), Decimal("0.00"))
        issued_invoices = [
            invoice
            for invoice in customer_invoices
            if invoice.status not in {SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.VOIDED}
        ]
        invoiced_total = sum((invoice.total for invoice in issued_invoices), Decimal("0.00"))
        paid_total = sum((invoice.amount_paid for invoice in issued_invoices), Decimal("0.00"))
        receivable_total = sum((invoice.amount_due for invoice in issued_invoices), Decimal("0.00"))
        unbilled_total = sum((order.unbilled_total for order in customer_orders), Decimal("0.00"))
        entries.append(
            ClientHistoryEntry(
                customer=customer,
                ordered_total=ordered_total.quantize(Decimal("0.01")),
                invoiced_total=invoiced_total.quantize(Decimal("0.01")),
                paid_total=paid_total.quantize(Decimal("0.01")),
                receivable_total=receivable_total.quantize(Decimal("0.01")),
                unbilled_total=unbilled_total.quantize(Decimal("0.01")),
                sales_orders=customer_orders,
                sales_invoices=customer_invoices,
                customer_receipts=customer_receipt_rows,
            )
        )

    entries.sort(key=lambda entry: entry.customer.name.lower())
    return ClientHistoryReport(
        ordered_total=sum((entry.ordered_total for entry in entries), Decimal("0.00")).quantize(Decimal("0.01")),
        invoiced_total=sum((entry.invoiced_total for entry in entries), Decimal("0.00")).quantize(Decimal("0.01")),
        paid_total=sum((entry.paid_total for entry in entries), Decimal("0.00")).quantize(Decimal("0.01")),
        receivable_total=sum((entry.receivable_total for entry in entries), Decimal("0.00")).quantize(Decimal("0.01")),
        unbilled_total=sum((entry.unbilled_total for entry in entries), Decimal("0.00")).quantize(Decimal("0.01")),
        clients=entries,
    )


def project_profitability(db: Session) -> ProjectProfitabilityReport:
    projects = list_projects(db)
    invoices = list_sales_invoices(db, limit=1000)
    transactions = list_operational_transactions(db, limit=1000)
    supplier_bills = list_supplier_bills(db, limit=1000)
    rows: list[ProjectProfitabilityRow] = []
    for project in projects:
        project_invoices = [
            invoice
            for invoice in invoices
            if invoice.project_id == project.id and invoice.status not in {SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.VOIDED}
        ]
        project_transactions = [
            transaction
            for transaction in transactions
            if transaction.project_id == project.id and transaction.status == TransactionStatus.POSTED
        ]
        project_supplier_bills = [
            bill
            for bill in supplier_bills
            if bill.project_id == project.id and bill.status == SupplierBillStatus.POSTED
        ]
        invoiced_total = sum((invoice.total for invoice in project_invoices), Decimal("0.00")).quantize(Decimal("0.01"))
        revenue_recognized = sum((invoice.subtotal for invoice in project_invoices), Decimal("0.00")).quantize(Decimal("0.01"))
        direct_costs = sum(
            (transaction.amount for transaction in project_transactions if transaction.kind == TransactionKind.EXPENSE),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))
        direct_costs = (
            direct_costs + sum((bill.subtotal for bill in project_supplier_bills), Decimal("0.00"))
        ).quantize(Decimal("0.01"))
        gross_profit = (revenue_recognized - direct_costs).quantize(Decimal("0.01"))
        gross_margin = None if revenue_recognized == 0 else (gross_profit / revenue_recognized).quantize(Decimal("0.0001"))
        rows.append(
            ProjectProfitabilityRow(
                project=project,
                contract_value=project.contract_value,
                invoiced_total=invoiced_total,
                revenue_recognized=revenue_recognized,
                direct_costs=direct_costs,
                gross_profit=gross_profit,
                gross_margin=gross_margin,
                receipts_count=sum(1 for transaction in project_transactions if transaction.receipt_id is not None),
            )
        )

    return ProjectProfitabilityReport(
        contract_value=sum((row.contract_value for row in rows), Decimal("0.00")).quantize(Decimal("0.01")),
        invoiced_total=sum((row.invoiced_total for row in rows), Decimal("0.00")).quantize(Decimal("0.01")),
        revenue_recognized=sum((row.revenue_recognized for row in rows), Decimal("0.00")).quantize(Decimal("0.01")),
        direct_costs=sum((row.direct_costs for row in rows), Decimal("0.00")).quantize(Decimal("0.01")),
        gross_profit=sum((row.gross_profit for row in rows), Decimal("0.00")).quantize(Decimal("0.01")),
        rows=rows,
    )


def _ar_bucket_name(entry_date: date, as_of: date) -> str:
    age_days = max((as_of - entry_date).days, 0)
    if age_days <= 30:
        return "current"
    if age_days <= 60:
        return "days_31_60"
    if age_days <= 90:
        return "days_61_90"
    return "days_over_90"


def accounts_receivable_ageing(db: Session, as_of: date | None = None) -> AccountsReceivableAgeingReport:
    report_date = as_of or date.today()
    totals = {
        "current": Decimal("0.00"),
        "days_31_60": Decimal("0.00"),
        "days_61_90": Decimal("0.00"),
        "days_over_90": Decimal("0.00"),
    }
    row_buckets_by_customer: dict[tuple[int | None, str], dict[str, Decimal]] = {}

    invoices = db.scalars(
        sales_invoice_query()
        .where(SalesInvoice.status.notin_([SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.VOIDED]))
        .where(SalesInvoice.issue_date <= report_date)
    ).all()
    for invoice in invoices:
        if invoice.amount_due <= 0:
            continue
        key = (invoice.customer_id, invoice.customer.name)
        buckets = row_buckets_by_customer.setdefault(
            key,
            {
                "current": Decimal("0.00"),
                "days_31_60": Decimal("0.00"),
                "days_61_90": Decimal("0.00"),
                "days_over_90": Decimal("0.00"),
            },
        )
        bucket = _ar_bucket_name(invoice.due_date, report_date)
        buckets[bucket] += invoice.amount_due

    ar_account = _get_account_by_code(db, "1100")
    rows = db.execute(
        select(
            JournalEntry.entry_date,
            JournalEntry.id,
            JournalLine.debit,
            JournalLine.credit,
            Contact.id,
            Contact.name,
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .outerjoin(OperationalTransaction, OperationalTransaction.journal_entry_id == JournalEntry.id)
        .outerjoin(SalesInvoice, SalesInvoice.journal_entry_id == JournalEntry.id)
        .outerjoin(CustomerReceipt, CustomerReceipt.journal_entry_id == JournalEntry.id)
        .outerjoin(Contact, Contact.id == OperationalTransaction.contact_id)
        .where(JournalLine.account_id == ar_account.id)
        .where(JournalEntry.entry_date <= report_date)
        .where(SalesInvoice.id.is_(None))
        .where(CustomerReceipt.id.is_(None))
        .order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)
    ).all()

    lots_by_customer: dict[tuple[int | None, str], list[dict[str, object]]] = {}
    all_lots: list[dict[str, object]] = []

    def apply_credit(lots: list[dict[str, object]], credit_amount: Decimal) -> Decimal:
        remaining_credit = credit_amount
        for lot in lots:
            if remaining_credit <= 0:
                break
            lot_amount = lot["amount"]
            if not isinstance(lot_amount, Decimal) or lot_amount <= 0:
                continue
            applied = min(lot_amount, remaining_credit)
            lot["amount"] = lot_amount - applied
            remaining_credit -= applied
        return remaining_credit

    for entry_date, _entry_id, debit, credit, customer_id, customer_name in rows:
        key = (customer_id, customer_name or "Unassigned")
        lots = lots_by_customer.setdefault(key, [])
        debit_amount = Decimal(debit or 0)
        credit_amount = Decimal(credit or 0)
        if debit_amount > 0:
            lot = {"date": entry_date, "amount": debit_amount}
            lots.append(lot)
            all_lots.append(lot)
        if credit_amount > 0:
            if customer_id is None:
                apply_credit(all_lots, credit_amount)
            else:
                apply_credit(lots, credit_amount)

    for (customer_id, customer_name), lots in lots_by_customer.items():
        buckets = row_buckets_by_customer.setdefault(
            (customer_id, customer_name),
            {
                "current": Decimal("0.00"),
                "days_31_60": Decimal("0.00"),
                "days_61_90": Decimal("0.00"),
                "days_over_90": Decimal("0.00"),
            },
        )
        for lot in lots:
            amount = lot["amount"]
            lot_date = lot["date"]
            if not isinstance(amount, Decimal) or not isinstance(lot_date, date) or amount <= 0:
                continue
            bucket = _ar_bucket_name(lot_date, report_date)
            buckets[bucket] += amount

    ageing_rows: list[AccountsReceivableAgeingRow] = []
    for (customer_id, customer_name), buckets in row_buckets_by_customer.items():
        row_total = sum(buckets.values(), Decimal("0.00"))
        if row_total <= 0:
            continue
        for bucket, amount in buckets.items():
            totals[bucket] += amount
        ageing_rows.append(
            AccountsReceivableAgeingRow(
                customer_id=customer_id,
                customer_name=customer_name,
                current=buckets["current"].quantize(Decimal("0.01")),
                days_31_60=buckets["days_31_60"].quantize(Decimal("0.01")),
                days_61_90=buckets["days_61_90"].quantize(Decimal("0.01")),
                days_over_90=buckets["days_over_90"].quantize(Decimal("0.01")),
                total=row_total.quantize(Decimal("0.01")),
            )
        )

    ageing_rows.sort(key=lambda row: (row.customer_name.lower(), row.customer_id or 0))
    total = sum(totals.values(), Decimal("0.00"))
    return AccountsReceivableAgeingReport(
        as_of=report_date,
        current=totals["current"].quantize(Decimal("0.01")),
        days_31_60=totals["days_31_60"].quantize(Decimal("0.01")),
        days_61_90=totals["days_61_90"].quantize(Decimal("0.01")),
        days_over_90=totals["days_over_90"].quantize(Decimal("0.01")),
        total=total.quantize(Decimal("0.01")),
        rows=ageing_rows,
    )


def accounts_payable_ageing(db: Session, as_of: date | None = None) -> AccountsPayableAgeingReport:
    report_date = as_of or date.today()
    totals = {
        "current": Decimal("0.00"),
        "days_31_60": Decimal("0.00"),
        "days_61_90": Decimal("0.00"),
        "days_over_90": Decimal("0.00"),
    }
    row_buckets_by_vendor: dict[tuple[int | None, str], dict[str, Decimal]] = {}

    bills = db.scalars(
        supplier_bill_query()
        .where(SupplierBill.status == SupplierBillStatus.POSTED)
        .where(SupplierBill.bill_date <= report_date)
    ).all()
    for bill in bills:
        if bill.amount_due <= 0:
            continue
        key = (bill.vendor_id, bill.vendor.name)
        buckets = row_buckets_by_vendor.setdefault(
            key,
            {
                "current": Decimal("0.00"),
                "days_31_60": Decimal("0.00"),
                "days_61_90": Decimal("0.00"),
                "days_over_90": Decimal("0.00"),
            },
        )
        bucket = _ar_bucket_name(bill.due_date, report_date)
        buckets[bucket] += bill.amount_due

    ageing_rows: list[AccountsPayableAgeingRow] = []
    for (vendor_id, vendor_name), buckets in row_buckets_by_vendor.items():
        row_total = sum(buckets.values(), Decimal("0.00"))
        if row_total <= 0:
            continue
        for bucket, amount in buckets.items():
            totals[bucket] += amount
        ageing_rows.append(
            AccountsPayableAgeingRow(
                vendor_id=vendor_id,
                vendor_name=vendor_name,
                current=buckets["current"].quantize(Decimal("0.01")),
                days_31_60=buckets["days_31_60"].quantize(Decimal("0.01")),
                days_61_90=buckets["days_61_90"].quantize(Decimal("0.01")),
                days_over_90=buckets["days_over_90"].quantize(Decimal("0.01")),
                total=row_total.quantize(Decimal("0.01")),
            )
        )

    ageing_rows.sort(key=lambda row: (row.vendor_name.lower(), row.vendor_id or 0))
    total = sum(totals.values(), Decimal("0.00"))
    return AccountsPayableAgeingReport(
        as_of=report_date,
        current=totals["current"].quantize(Decimal("0.01")),
        days_31_60=totals["days_31_60"].quantize(Decimal("0.01")),
        days_61_90=totals["days_61_90"].quantize(Decimal("0.01")),
        days_over_90=totals["days_over_90"].quantize(Decimal("0.01")),
        total=total.quantize(Decimal("0.01")),
        rows=ageing_rows,
    )
