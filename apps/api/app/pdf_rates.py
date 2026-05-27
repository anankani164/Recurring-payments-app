import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import pdfplumber

DATE_PATTERNS = [
    # "27 May 2026", "27-May-2026", "27/May/2026"
    re.compile(r"(\d{1,2})[\-/\s]([A-Za-z]{3,9})[\-/\s](\d{4})"),
    # "2026-05-27"
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    # "27/05/2026", "27-05-2026", "27.05.2026"
    re.compile(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})"),
    # "May 27, 2026" or "May 27 2026"
    re.compile(r"([A-Za-z]{3,9})\s+(\d{1,2})[,\s]+(\d{4})"),
    # "27TH MAY, 2026" / "27th May 2026" / "27 th May 2026" (ordinal, superscript-safe)
    re.compile(r"(\d{1,2})\s*(?:ST|ND|RD|TH|st|nd|rd|th)[,\s]+([A-Za-z]{3,9})[,\s]+(\d{4})"),
]


class PdfParseError(ValueError):
    pass


def _extract_text_via_ocr(pdf_path: Path) -> Optional[str]:
    """
    Optional OCR fallback for scanned/image-only PDFs.
    Requires pytesseract and a working tesseract binary in the runtime image.
    """
    try:
        import pytesseract  # type: ignore
    except Exception:  # noqa: BLE001
        return None

    chunks: list[str] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_img = page.to_image(resolution=200).original
                text = pytesseract.image_to_string(page_img) or ""
                if text.strip():
                    chunks.append(text)
    except Exception:  # noqa: BLE001
        return None

    combined = "\n".join(chunks).strip()
    return combined or None


def _extract_rates_from_row(normalized: list[str], code: str) -> dict | None:
    if code not in normalized:
        return None
    code_index = normalized.index(code)
    if code_index + 4 >= len(normalized):
        return None
    try:
        return {
            "code": code,
            "cash_buying": _to_num(normalized[code_index + 1]),
            "cash_selling": _to_num(normalized[code_index + 2]),
            "tts_buying": _to_num(normalized[code_index + 3]),
            "tts_selling": _to_num(normalized[code_index + 4]),
        }
    except ValueError:
        return None


def _extract_rates_from_text(text: str, code: str) -> dict | None:
    # Handles layouts where table extraction fails but rows are present in plain text.
    # Example row: "US DOLLAR USD 10.1 10.2 10.3 10.4"
    pattern = re.compile(
        rf"\b{re.escape(code)}\b\s+([\d,]+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)"
    )
    match = pattern.search(text)
    if not match:
        return None
    values = match.groups()
    return {
        "code": code,
        "cash_buying": _to_num(values[0]),
        "cash_selling": _to_num(values[1]),
        "tts_buying": _to_num(values[2]),
        "tts_selling": _to_num(values[3]),
    }


def _parse_date(text: str):
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        g = match.groups()
        candidates = []
        try:
            if len(g[0]) == 4:
                # YYYY-MM-DD
                candidates.append(datetime.strptime(f"{g[0]}-{g[1]}-{g[2]}", "%Y-%m-%d").date())
            elif g[0].isalpha():
                # Month DD YYYY
                for fmt in ("%B %d %Y", "%b %d %Y"):
                    try:
                        candidates.append(datetime.strptime(f"{g[0]} {g[1]} {g[2]}", fmt).date())
                        break
                    except ValueError:
                        pass
            elif g[1].isalpha():
                # DD Month YYYY  (original pattern + ordinal pattern)
                for fmt in ("%d %B %Y", "%d %b %Y"):
                    try:
                        candidates.append(datetime.strptime(f"{g[0]} {g[1]} {g[2]}", fmt).date())
                        break
                    except ValueError:
                        pass
            else:
                # DD/MM/YYYY — assume day-first (Ghanaian bank convention)
                try:
                    candidates.append(datetime.strptime(f"{g[0]}/{g[1]}/{g[2]}", "%d/%m/%Y").date())
                except ValueError:
                    pass
        except (ValueError, IndexError):
            pass
        for d in candidates:
            if d.year >= 2000:
                return d
    raise PdfParseError("Could not find/parse rate date from PDF text")


def _to_num(raw: str) -> float:
    return float(raw.replace(",", "").strip())


def _parse_from_path(pdf_path: Path, target_code: str) -> dict:
    """Core parsing logic — operates on a local file path."""
    code = target_code.upper().strip()
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        rate_date = _parse_date(text)

        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    if not row:
                        continue
                    normalized = [str(col).strip() if col else "" for col in row]
                    extracted = _extract_rates_from_row(normalized, code)
                    if extracted:
                        return {"rate_date": rate_date, **extracted}

        extracted = _extract_rates_from_text(text, code)
        if extracted:
            return {"rate_date": rate_date, **extracted}

        ocr_text = _extract_text_via_ocr(pdf_path)
        if ocr_text:
            try:
                ocr_date = _parse_date(ocr_text)
            except PdfParseError:
                ocr_date = rate_date
            extracted = _extract_rates_from_text(ocr_text, code)
            if extracted:
                return {"rate_date": ocr_date, **extracted}

    raise PdfParseError(f"Could not find {code} rates in PDF table, text, or OCR fallback")


def parse_bank_pdf_rates(source_url: str, target_code: str = "USD") -> dict:
    code = target_code.upper().strip()
    if not code:
        raise PdfParseError("target_code is required")

    response = httpx.get(
        source_url,
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    with tempfile.NamedTemporaryFile(prefix="fx_source_", suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(response.content)
        temp_path = Path(tmp_file.name)

    try:
        return _parse_from_path(temp_path, code)
    finally:
        temp_path.unlink(missing_ok=True)


def parse_uploaded_pdf(pdf_bytes: bytes, target_code: str = "USD") -> dict:
    """Parse rates from raw PDF bytes (file upload path)."""
    code = target_code.upper().strip()
    if not code:
        raise PdfParseError("target_code is required")

    with tempfile.NamedTemporaryFile(prefix="fx_upload_", suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(pdf_bytes)
        temp_path = Path(tmp_file.name)

    try:
        return _parse_from_path(temp_path, code)
    finally:
        temp_path.unlink(missing_ok=True)
