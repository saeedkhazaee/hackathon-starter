"""Deterministic synthetic supplier inbox. Changes to this file invalidate scoring."""
import base64
import csv
import io
import random
from .models import Batch, Document, SourceVersion


def business_text(kind="invoice", number=1, rows=3, seed=17, discrepancy=0):
    rng = random.Random(seed)
    if kind == "contract":
        return (f"Services Contract\nContract ID: CT-{number}\nParty A: Cedar Systems\nParty B: Maple Works\n"
                "Effective Date: 2026-01-01\nExpiration Date: 2026-12-31\nContract Type: Maintenance\n")
    title = {"invoice": "Tax Invoice", "purchase_order": "Purchase Order", "receipt": "Sales Receipt"}[kind]
    identity = {"invoice": f"Invoice Number: INV-{number}\nSupplier: Cedar Systems\nCustomer: Maple Works",
                "purchase_order": f"Order Number: PO-{number}\nSupplier: Cedar Systems\nCustomer: Maple Works",
                "receipt": "Merchant: Cedar Store"}[kind]
    body = io.StringIO(newline="")
    writer = csv.writer(body, lineterminator="\n")
    writer.writerow(["description", "quantity", "unit_cents"])
    subtotal = 0
    for index in range(rows):
        quantity, price = rng.randint(1, 5), rng.randint(100, 900)
        writer.writerow([f"Service {index + 1}", quantity, price])
        subtotal += quantity * price
    tax = (subtotal * 5 + 50) // 100
    return (f"{title}\n{identity}\nDate: 2026-10-15\nSubtotal Cents: {subtotal}\n"
            f"Tax Cents: {tax}\nTotal Cents: {subtotal + tax + discrepancy}\nItems:\n{body.getvalue()}")


def text_document(document_id, text, *, ready=True):
    return Document(document_id=str(document_id), filename=f"{document_id}.txt",
                    versions=[SourceVersion(text=text, ready=ready)])


def digital_pdf(text, split_at=None):
    """A deterministic synthetic PDF with a standard built-in font."""
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    lines = text.splitlines()
    groups = [lines] if split_at is None else [lines[:split_at], lines[split_at:]]
    for group in groups:
        if len(group) > 48:
            raise ValueError("Fixture PDF page exceeds 48 lines")
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        commands = ["BT /F1 11 Tf 40 750 Td 14 TL"]
        for line in group:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"({escaped}) Tj T*")
        commands.append("ET")
        stream.set_data("\n".join(commands).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def narrative_text(kind="invoice", number=1, seed=17):
    """Mixed prose and structured data from a supplier's document export."""
    text = business_text(kind, number, seed=seed)
    if kind == "contract":
        remove = ("Party A:", "Effective Date:")
        prose = ["Maple Works is the customer. The provider signing as the first party is Cedar Systems.",
                 "Although discussions began in December, the agreement takes effect on January 1, 2026."]
    elif kind == "receipt":
        remove = ("Merchant:", "Date:")
        prose = ["The card processor is Pine Payments; the store that sold these items is Cedar Store.",
                 "This receipt records the purchase made on October 15, 2026, not the October 18 posting date."]
    else:
        remove = ("Supplier:", "Date:")
        prose = ["Maple Works is the purchaser. The listed services are supplied by Cedar Systems.",
                 "The document was issued on October 15, 2026; payment is due on November 14, 2026."]
    if number >= 4:
        prose.reverse()
    lines = [line for line in text.splitlines() if not line.startswith(remove)]
    position = lines.index("Items:") if "Items:" in lines else len(lines)
    lines[position:position] = ["Narrative:", *prose, "End Narrative"]
    return "\n".join(lines) + "\n"


def make_workload(seed=17, rows=25_000, *, language_assisted=False):
    if not 1 <= rows <= 25_000:
        raise ValueError("rows must be between 1 and 25,000")
    docs = []
    kinds = ["invoice", "purchase_order", "receipt", "contract"]
    for index in range(28):
        generator = narrative_text if language_assisted and index < 8 else business_text
        docs.append(text_document(f"DOC-{index:03}", generator(kinds[index % 4], index, seed=seed + index)))
    for index in range(8):
        docs.append(text_document(f"DOC-{28 + index:03}", business_text("invoice", 28 + index,
            rows=rows, seed=seed + index, discrepancy=1 if index in (2, 5, 7) else 0)))
    docs.append(text_document("DOC-036", business_text("purchase_order", 36, rows=min(rows * 2, 50_000), seed=seed)))
    docs.append(text_document("DOC-037", docs[28].versions[0].text))
    pending = text_document("DOC-038", business_text("receipt", 38, seed=seed), ready=False)
    pending.versions.append(SourceVersion(text=business_text("receipt", 38, seed=seed)))
    docs.append(pending)
    pdf = digital_pdf(business_text("invoice", 39, seed=seed + 99), split_at=5)
    docs.append(Document(document_id="DOC-039", filename="DOC-039.pdf",
                         versions=[SourceVersion(content_base64=base64.b64encode(pdf).decode())]))
    return Batch(documents=docs)


def binary_document(path, document_id=None):
    from pathlib import Path
    path = Path(path)
    return Document(document_id=document_id or path.stem, filename=path.name,
                    versions=[SourceVersion(content_base64=base64.b64encode(path.read_bytes()).decode())])
