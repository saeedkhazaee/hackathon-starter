"""Shared processing path for API and CLI."""
from .classification import MODEL
from .extraction import extract
from .ingestion import extract_text
from .validation import validate


def process(version, budget, checkpoint):
    checkpoint("ingestion")
    text, detected_format, pages = extract_text(version, budget)
    checkpoint("classification")
    budget.stage()
    classification = MODEL.predict(text)
    checkpoint("extraction")
    fields, citations = extract(text, classification["category"], budget)
    checkpoint("validation")
    validate(fields, classification["category"], budget)
    checkpoint("complete")
    return {"classification": classification, "format": detected_format, "pages": pages,
            "fields": fields, "citations": citations}
