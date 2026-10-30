"""Structured extraction for the documented business exchange format."""
import csv
import io
import re
from .safety import PermanentError, MAX_ROWS

FIELDS = {
    "invoice": ("invoice_number", "supplier", "customer", "date", "items", "subtotal_cents", "tax_cents", "total_cents"),
    "purchase_order": ("order_number", "supplier", "customer", "date", "items", "subtotal_cents", "tax_cents", "total_cents"),
    "receipt": ("merchant", "date", "items", "subtotal_cents", "tax_cents", "total_cents"),
    "contract": ("contract_id", "party_a", "party_b", "effective_date", "expiration_date", "contract_type"),
}


def integer(value, field):
    if not re.fullmatch(r"[0-9]{1,12}", value):
        raise PermanentError("invalid_number", f"{field} must be a nonnegative integer")
    return int(value)


def read_document(text, budget):
    budget.stage()
    header, marker, body = text.partition("Items:")
    fields, sources = {}, {}
    for number, line in enumerate(header.splitlines(), 1):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        if key in fields:
            raise PermanentError("duplicate_field", f"Duplicate header: {key}")
        fields[key], sources[key] = value.strip(), number
    for key in ("subtotal_cents", "tax_cents", "total_cents"):
        if key in fields:
            fields[key] = integer(fields[key], key)
    if marker:
        lines = body.lstrip("\r\n")
        reader = csv.DictReader(io.StringIO(lines))
        if reader.fieldnames != ["description", "quantity", "unit_cents"]:
            raise PermanentError("invalid_table", "Expected description,quantity,unit_cents columns")
        items = []
        for index, row in enumerate(reader):
            if index % 128 == 0:
                budget.check()
            if index >= MAX_ROWS:
                raise PermanentError("row_limit", "Document exceeds 50,000 line items")
            if None in row or any(value is None for value in row.values()):
                raise PermanentError("invalid_table", "Line item has the wrong number of columns")
            quantity, price = integer(row["quantity"].strip(), "quantity"), integer(row["unit_cents"].strip(), "unit_cents")
            if not row["description"].strip() or quantity < 1:
                raise PermanentError("invalid_item", "Line items require a description and positive quantity")
            items.append({"description": row["description"].strip(), "quantity": quantity,
                          "unit_cents": price, "amount_cents": quantity * price})
        if not items:
            raise PermanentError("empty_items", "At least one line item is required")
        fields["items"] = items
        sources["items"] = len(header.splitlines()) + 1
    return fields, sources


def extract(text, category, budget):
    if category not in FIELDS:
        raise PermanentError("unknown_document", "Document type is outside the trained scope")
    result, citations = {}, {}
    for field in FIELDS[category]:
        view, locations = read_document(text, budget)
        if field not in view or view[field] == "":
            raise PermanentError("missing_field", f"Missing required field: {field}")
        result[field] = view[field]
        citations[field] = {"text_line": locations[field]}
    return result, citations
