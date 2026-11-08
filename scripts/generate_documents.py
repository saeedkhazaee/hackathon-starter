"""Regenerate small public examples; Pillow is needed only for the optional PNG."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docflow.workload import business_text, narrative_text, digital_pdf, make_workload, binary_document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true")
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / "data/documents"
    target.mkdir(parents=True, exist_ok=True)
    for kind in ("invoice", "purchase_order", "receipt", "contract"):
        text = business_text(kind)
        (target / f"{kind}.txt").write_text(text, encoding="utf-8")
        (target / f"{kind}.pdf").write_bytes(digital_pdf(text, split_at=4))
    for index in range(8):
        kind = ("invoice", "purchase_order", "receipt", "contract")[index % 4]
        (target / f"{kind}-narrative-{index // 4 + 1}.txt").write_text(
            narrative_text(kind, index), encoding="utf-8")
    if args.scan:
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.load_default(size=30)
        text = business_text("contract")
        image = Image.new("RGB", (1600, 500), "white")
        ImageDraw.Draw(image).multiline_text((45, 35), text, font=font, fill="black", spacing=12)
        image.save(target / "contract_scan.png")
        batch = make_workload(rows=10)
        batch.documents[3] = binary_document(target / "contract_scan.png", "DOC-003")
        fixtures = target.parent / "fixtures"
        fixtures.mkdir(exist_ok=True)
        (fixtures / "ocr_workload.json").write_text(batch.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote synthetic examples to {target}")


if __name__ == "__main__":
    main()
