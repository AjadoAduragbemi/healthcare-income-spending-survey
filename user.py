"""
User class for the healthcare income-spending survey.

A User is one survey participant. The same class is used by the Flask app
(form -> MongoDB document) and by export_to_csv.py (MongoDB document -> CSV row).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Expense categories: form/database key -> display label
EXPENSE_CATEGORIES = {
    "utilities": "Utilities",
    "entertainment": "Entertainment",
    "school_fees": "School fees",
    "shopping": "Shopping",
    "healthcare": "Healthcare",
}
GENDERS = ("Female", "Male", "Non-binary", "Prefer not to say")
MIN_AGE, MAX_AGE = 18, 100


class ValidationError(Exception):
    """Raised when submitted survey data is invalid. Holds a list of messages."""

    def __init__(self, messages):
        super().__init__("; ".join(messages))
        self.messages = messages


def _parse_number(raw, field_name, errors, integer=False):
    """Convert form text to a non-negative number, recording a message if it isn't one."""
    if raw in ("", None):
        errors.append(f"{field_name} is required.")
        return None
    try:
        value = int(raw) if integer else round(float(raw), 2)
    except (TypeError, ValueError):
        errors.append(f"{field_name} must be a number.")
        return None
    if value < 0:
        errors.append(f"{field_name} cannot be negative.")
        return None
    return value


@dataclass
class User:
    """One survey participant: age, gender, total income and expenses by category."""

    age: int
    gender: str
    total_income: float
    expenses: dict = field(default_factory=dict)       # category key -> amount (ticked categories only)
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "survey"                              # "survey" (web form) or "synthetic" (seed script)

    CSV_FIELDS = (["age", "gender", "total_income"]
                  + list(EXPENSE_CATEGORIES)
                  + ["total_expenses", "submitted_at", "source"])

    @property
    def total_expenses(self):
        return round(sum(self.expenses.values()), 2)

    # ---- Creating users ---------------------------------------------------
    @classmethod
    def from_form(cls, form):
        """Validate web-form data and return a User, or raise ValidationError."""
        errors = []

        age = _parse_number(form.get("age", "").strip(), "Age", errors, integer=True)
        if age is not None and not MIN_AGE <= age <= MAX_AGE:
            errors.append(f"Age must be between {MIN_AGE} and {MAX_AGE}.")

        gender = form.get("gender", "")
        if gender not in GENDERS:
            errors.append("Please select a gender option.")

        income = _parse_number(form.get("total_income", "").strip(), "Total income", errors)

        expenses = {}
        for key, label in EXPENSE_CATEGORIES.items():
            if form.get(f"expense_{key}"):                       # Checkbox ticked
                raw_amount = form.get(f"amount_{key}", "").strip()
                if not raw_amount:
                    errors.append(f"Enter an amount for {label}, or untick it.")
                    continue
                amount = _parse_number(raw_amount, f"{label} amount", errors)
                if amount is not None:
                    expenses[key] = amount

        if errors:
            raise ValidationError(errors)
        return cls(age=age, gender=gender, total_income=income, expenses=expenses)

    @classmethod
    def from_document(cls, document):
        """Rebuild a User from a MongoDB document."""
        return cls(
            age=int(document["age"]),
            gender=document["gender"],
            total_income=float(document["total_income"]),
            expenses={k: float(v) for k, v in document.get("expenses", {}).items()},
            submitted_at=document.get("submitted_at") or datetime.now(timezone.utc),
            source=document.get("source", "survey"),
        )

    # ---- Converting users -------------------------------------------------
    def to_document(self):
        """Return the dictionary stored in MongoDB."""
        return {
            "age": self.age,
            "gender": self.gender,
            "total_income": self.total_income,
            "expenses": self.expenses,
            "total_expenses": self.total_expenses,
            "submitted_at": self.submitted_at,
            "source": self.source,
        }

    def to_csv_row(self):
        """Return a flat row for the CSV: one column per expense category (0 if not ticked)."""
        row = {"age": self.age, "gender": self.gender, "total_income": self.total_income}
        row.update({key: self.expenses.get(key, 0.0) for key in EXPENSE_CATEGORIES})
        row.update({
            "total_expenses": self.total_expenses,
            "submitted_at": self.submitted_at.isoformat(),
            "source": self.source,
        })
        return row
