import pytest

from app.pdf_rates import PdfParseError, _extract_rates_from_row, _extract_rates_from_text, _parse_date


def test_parse_date_ymd():
    assert _parse_date("Forex rates for 2026-05-26").isoformat() == "2026-05-26"


def test_parse_date_failure():
    with pytest.raises(PdfParseError):
        _parse_date("no date here")


# ── Stanbic Bank PDF format ──────────────────────────────────────────────────
# Header line: "Forex Rates – 26th May 2026"
# "th" is a superscript in the PDF; pdfplumber may emit it as "26th" or "26 th"

def test_parse_date_ordinal_attached():
    # pdfplumber keeps "th" attached: "26th May 2026"
    assert _parse_date("Forex Rates – 26th May 2026").isoformat() == "2026-05-26"


def test_parse_date_ordinal_spaced():
    # pdfplumber emits superscript with a leading space: "26 th May 2026"
    assert _parse_date("Forex Rates – 26 th May 2026").isoformat() == "2026-05-26"


def test_parse_date_ordinal_uppercase():
    assert _parse_date("RATES AS AT 6TH MAY 2026").isoformat() == "2026-05-06"


def test_parse_date_dd_mm_yyyy():
    assert _parse_date("Date: 26/05/2026").isoformat() == "2026-05-26"


def test_parse_date_month_first():
    assert _parse_date("Effective Date: May 26, 2026").isoformat() == "2026-05-26"


# ── Table row extraction (Stanbic 6-column layout) ──────────────────────────
# pdfplumber produces rows like:
#   ["United States Dollars", "USD", "11.3800", "12.2200", "11.3800", "11.7500"]

def test_extract_rates_from_row_stanbic_usd():
    row = ["United States Dollars", "USD", "11.3800", "12.2200", "11.3800", "11.7500"]
    result = _extract_rates_from_row(row, "USD")
    assert result is not None
    assert result["code"] == "USD"
    assert result["cash_buying"] == 11.38
    assert result["cash_selling"] == 12.22
    assert result["tts_buying"] == 11.38
    assert result["tts_selling"] == 11.75


def test_extract_rates_from_row_missing_code():
    # Row for a currency we're not looking for should return None
    row = ["Euro", "EUR", "13.1553", "14.2974", "13.1553", "13.7475"]
    assert _extract_rates_from_row(row, "USD") is None


def test_extract_rates_from_row_dash_values():
    # CAD row has dashes for Cash; _to_num raises ValueError → returns None gracefully
    row = ["Canadian Dollar", "CAD", "-", "-", "8.2107", "8.5560"]
    assert _extract_rates_from_row(row, "CAD") is None


# ── Text fallback (if table extraction misses) ───────────────────────────────

def test_extract_rates_from_text_stanbic():
    text = (
        "Forex Rates – 26th May 2026\n"
        "Currency Code Cash TTs\n"
        "Buying Selling Buying Selling\n"
        "United States Dollars USD 11.3800 12.2200 11.3800 11.7500\n"
        "South African Rand ZAR 0.6855 0.7590 0.6855 0.7298\n"
    )
    result = _extract_rates_from_text(text, "USD")
    assert result is not None
    assert result["cash_buying"] == 11.38
    assert result["tts_selling"] == 11.75


def test_extract_rates_from_text_fallback():
    text = "FX SHEET\nUSD 11.11 11.22 11.33 11.44\n"
    parsed = _extract_rates_from_text(text, "USD")
    assert parsed is not None
    assert parsed["cash_buying"] == 11.11


def test_extract_rates_from_row_basic():
    row = ["US Dollar", "USD", "10.10", "10.20", "10.30", "10.40"]
    parsed = _extract_rates_from_row(row, "USD")
    assert parsed is not None
    assert parsed["tts_selling"] == 10.40
