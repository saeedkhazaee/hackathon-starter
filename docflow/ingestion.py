"""Text, digital PDF and optional PNG OCR. No network document fetching."""
import io
import shutil
import subprocess
import tempfile
from pathlib import Path
from pypdf import PdfReader
from .safety import PermanentError, TransientError, MAX_PAGES


def extract_text(version, budget):
    budget.stage()
    if not version.ready:
        raise TransientError("source_pending", "Supplier snapshot is not finalized")
    payload = version.bytes()
    if payload.startswith(b"%PDF-"):
        try:
            reader = PdfReader(io.BytesIO(payload), strict=True)
            if reader.is_encrypted:
                raise PermanentError("encrypted_pdf", "Encrypted PDFs are outside the supported scope")
            if len(reader.pages) > MAX_PAGES:
                raise PermanentError("page_limit", "PDF exceeds 100 pages")
            parts = []
            size = 0
            for page in reader.pages:
                budget.check()
                text = page.extract_text() or ""
                size += len(text)
                if size > 4_000_000:
                    raise PermanentError("text_limit", "Extracted text exceeds 4 MB")
                parts.append(text)
            text = "\n".join(parts)
            if not text.strip():
                raise PermanentError("image_pdf", "Image-only PDF is unsupported; submit a PNG scan")
            return text, "pdf", len(parts)
        except PermanentError:
            raise
        except Exception as exc:
            # Stopped must retain its cancellation/deadline semantics.
            from .safety import Stopped
            if isinstance(exc, Stopped):
                raise
            raise PermanentError("invalid_pdf", "PDF could not be parsed") from exc
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return ocr(payload, budget), "png_ocr", 1
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError as exc:
        raise PermanentError("unsupported_format", "Use UTF-8 text, digital PDF or PNG") from exc
    if "\x00" in text:
        raise PermanentError("unsupported_format", "Binary input is not a supported text document")
    return text, "text", text.count("\f") + 1


def ocr(payload, budget):
    executable = shutil.which("tesseract")
    if not executable:
        raise PermanentError("ocr_unavailable", "Install Tesseract with English language data to process PNG scans")
    # Pixel bounds keep fixture OCR manageable even for a small compressed file.
    if len(payload) < 24:
        raise PermanentError("invalid_image", "Truncated PNG")
    width, height = int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")
    if not 0 < width * height <= 8_000_000:
        raise PermanentError("image_limit", "PNG exceeds the eight-megapixel limit")
    with tempfile.TemporaryDirectory(prefix="docflow-ocr-") as directory:
        path = Path(directory) / "document.png"
        path.write_bytes(payload)
        try:
            completed = subprocess.run([executable, str(path), "stdout", "-l", "eng", "--psm", "6"],
                                       capture_output=True, timeout=min(10, budget.remaining()), check=True)
        except subprocess.TimeoutExpired as exc:
            raise PermanentError("ocr_timeout", "OCR exceeded its ten-second limit") from exc
        except subprocess.CalledProcessError as exc:
            raise PermanentError("ocr_failed", "OCR could not read the PNG") from exc
    budget.check()
    return completed.stdout.decode("utf-8", errors="replace")
