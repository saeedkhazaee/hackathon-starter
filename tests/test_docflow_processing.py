import base64
from pathlib import Path
import shutil
import pytest
from docflow.jobs import process_batch
from docflow.models import Batch, Document, SourceVersion
from docflow.workload import text_document, binary_document, digital_pdf

INVOICE = """Invoice
Invoice Number: X-73
Supplier: North Supply
Customer: South Works
Date: 2026-02-28
Subtotal Cents: 1700
Tax Cents: 85
Total Cents: 1785
Items:
description,quantity,unit_cents
Cable,2,350
Service,1,1000
"""


def run(text):
    return process_batch(Batch(documents=[text_document("a", text)]))["documents"][0]


def test_invoice_fields_and_independent_arithmetic():
    record = run(INVOICE)
    assert record["status"] == "completed"
    result = record["result"]
    assert result["classification"]["category"] == "invoice"
    assert result["fields"] == {"invoice_number": "X-73", "supplier": "North Supply", "customer": "South Works",
        "date": "2026-02-28", "subtotal_cents": 1700, "tax_cents": 85, "total_cents": 1785,
        "items": [{"description": "Cable", "quantity": 2, "unit_cents": 350, "amount_cents": 700},
                  {"description": "Service", "quantity": 1, "unit_cents": 1000, "amount_cents": 1000}]}
    assert result["citations"]["supplier"] == {"text_line": 3}
    assert record["attempts"][-1]["checkpoints"][-1]["stage"] == "complete"


@pytest.mark.parametrize("text,code", [
    (INVOICE.replace("1785", "1786"), "arithmetic_mismatch"),
    (INVOICE.replace("2026-02-28", "2026-02-30"), "invalid_date"),
    (INVOICE.replace("Cable,2,350", "Cable,0,350"), "invalid_item"),
    (INVOICE.replace("Cable,2,350", "Cable,no,350"), "invalid_number"),
    (INVOICE.replace("Cable,2,350", "Cable,2,350,extra"), "invalid_table"),
    (INVOICE.replace("Supplier: North Supply", "Supplier:"), "missing_field"),
    (INVOICE.replace("Supplier: North Supply", "Supplier: North Supply\nSupplier: Override"), "duplicate_field"),
    ("unrelated nonsense xyz", "unknown_document"),
])
def test_controlled_failures(text, code):
    record = run(text)
    assert record["status"] == "failed"
    assert record["error"]["code"] == code
    assert record["result"] is None
    assert 1 <= record["attempt"] <= 12
    assert all(a["completed_at"] is not None for a in record["attempts"])


def test_changed_content_with_same_identity_and_duplicate_payload():
    first = run(INVOICE)
    second = run(INVOICE.replace("X-73", "X-74").replace("South Works", "East Works"))
    assert second["result"]["fields"]["invoice_number"] == "X-74"
    assert first["content_hash"] != second["content_hash"]
    docs = process_batch(Batch(documents=[text_document("a", INVOICE), text_document("b", INVOICE)]))["documents"]
    assert docs[0]["result"] == docs[1]["result"]
    assert docs[0]["content_hash"] == docs[1]["content_hash"]


@pytest.mark.parametrize("kind", ["invoice", "purchase_order", "receipt", "contract"])
@pytest.mark.parametrize("suffix", ["txt", "pdf"])
def test_public_documents(kind, suffix):
    path = Path(__file__).resolve().parents[1] / "data/documents" / f"{kind}.{suffix}"
    record = process_batch(Batch(documents=[binary_document(path)]))["documents"][0]
    assert record["status"] == "completed"
    assert record["result"]["classification"]["category"] == kind
    if suffix == "pdf":
        assert record["result"]["pages"] == 2


def test_pdf_preserves_fields():
    pdf = Document(document_id="pdf", filename="invoice.pdf", versions=[SourceVersion(
        content_base64=base64.b64encode(digital_pdf(INVOICE, split_at=5)).decode())])
    result = process_batch(Batch(documents=[pdf]))["documents"][0]["result"]
    assert result["fields"] == run(INVOICE)["result"]["fields"]


def test_missing_ocr_is_honest_failure(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    path = Path(__file__).resolve().parents[1] / "data/documents/contract_scan.png"
    record = process_batch(Batch(documents=[binary_document(path)]))["documents"][0]
    assert record["status"] == "failed"
    assert record["error"]["code"] == "ocr_unavailable"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Optional system OCR not installed")
def test_actual_scan_ocr():
    path = Path(__file__).resolve().parents[1] / "data/documents/contract_scan.png"
    record = process_batch(Batch(documents=[binary_document(path)]))["documents"][0]
    assert record["status"] == "completed"
    assert record["result"]["format"] == "png_ocr"
    assert record["result"]["fields"] == {"contract_id": "CT-1", "party_a": "Cedar Systems", "party_b": "Maple Works",
        "effective_date": "2026-01-01", "expiration_date": "2026-12-31", "contract_type": "Maintenance"}


def test_malformed_pdf_and_binary():
    for payload, code in [(b"%PDF-broken", "invalid_pdf"), (b"\x00\x01\x02", "unsupported_format")]:
        doc = Document(document_id="bad", filename="data", versions=[SourceVersion(content_base64=base64.b64encode(payload).decode())])
        record = process_batch(Batch(documents=[doc]))["documents"][0]
        assert record["error"]["code"] == code
