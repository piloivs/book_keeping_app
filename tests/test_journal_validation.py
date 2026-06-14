from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from bookkeeping_app.schemas import JournalEntryCreate


def test_journal_entry_must_balance() -> None:
    with pytest.raises(ValidationError):
        JournalEntryCreate(
            entry_date=date(2026, 6, 14),
            memo="Unbalanced entry",
            lines=[
                {"account_id": 1, "debit": Decimal("10.00")},
                {"account_id": 2, "credit": Decimal("9.99")},
            ],
        )


def test_journal_line_cannot_have_both_debit_and_credit() -> None:
    with pytest.raises(ValidationError):
        JournalEntryCreate(
            entry_date=date(2026, 6, 14),
            memo="Invalid line",
            lines=[
                {"account_id": 1, "debit": Decimal("10.00"), "credit": Decimal("10.00")},
                {"account_id": 2, "credit": Decimal("10.00")},
            ],
        )

