"""Business correctness, integer-cent totals and ISO dates."""
from datetime import date
from .safety import PermanentError


def validate(fields, category, budget):
    budget.stage()
    try:
        if category == "contract":
            start, end = date.fromisoformat(fields["effective_date"]), date.fromisoformat(fields["expiration_date"])
            if end < start:
                raise ValueError("date order")
        else:
            date.fromisoformat(fields["date"])
            subtotal = sum(item["amount_cents"] for item in fields["items"])
            if fields["subtotal_cents"] != subtotal or fields["total_cents"] != subtotal + fields["tax_cents"]:
                raise PermanentError("arithmetic_mismatch", "Line items, subtotal, tax and total do not reconcile")
    except ValueError as exc:
        raise PermanentError("invalid_date", "Dates must be valid ISO dates in chronological order") from exc
