import pytest

from app.pdf_rates import (
    PdfParseError,
    _detect_col_map,
    _extract_rates_from_row,
    _extract_rates_from_text,
    _parse_date,
)


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


# ── Absa Bank PDF format ──────────────────────────────────────────────────────
# Columns: CURRENCY | CODE | TRANSFER BUY | TRANSFER SELL | CASH BUY | CASH SELL
# pdfplumber produces merged-cell headers as None in continuation columns:
#   Row 0: ["", "", "TRANSFER", None, "CASH", None]
#   Row 1: ["CURRENCY", "CODE", "BUY", "SELL", "BUY", "SELL"]
#   Row 2: ["U.S. DOLLAR", "USD", "11.3500", "11.7500", "11.3500", "12.1700"]


def test_detect_col_map_absa_merged_headers():
    table = [
        ["", "", "TRANSFER", None, "CASH", None],
        ["CURRENCY", "CODE", "BUY", "SELL", "BUY", "SELL"],
        ["U.S. DOLLAR", "USD", "11.3500", "11.7500", "11.3500", "12.1700"],
    ]
    col_map = _detect_col_map(table)
    assert col_map is not None
    assert col_map[2] == "tts_buying"
    assert col_map[3] == "tts_selling"
    assert col_map[4] == "cash_buying"
    assert col_map[5] == "cash_selling"


def test_detect_col_map_stanbic_merged_headers():
    table = [
        ["", "", "CASH", None, "TTs", None],
        ["Currency", "Code", "Buying", "Selling", "Buying", "Selling"],
        ["United States Dollars", "USD", "11.3800", "12.2200", "11.3800", "11.7500"],
    ]
    col_map = _detect_col_map(table)
    assert col_map is not None
    assert col_map[2] == "cash_buying"
    assert col_map[3] == "cash_selling"
    assert col_map[4] == "tts_buying"
    assert col_map[5] == "tts_selling"


def test_detect_col_map_combined_headers():
    # Single-row headers: "TRANSFER BUY", "TRANSFER SELL", "CASH BUY", "CASH SELL"
    table = [
        ["CURRENCY", "CODE", "TRANSFER BUY", "TRANSFER SELL", "CASH BUY", "CASH SELL"],
        ["U.S. DOLLAR", "USD", "11.3500", "11.7500", "11.3500", "12.1700"],
    ]
    col_map = _detect_col_map(table)
    assert col_map is not None
    assert col_map[2] == "tts_buying"
    assert col_map[3] == "tts_selling"
    assert col_map[4] == "cash_buying"
    assert col_map[5] == "cash_selling"


def test_detect_col_map_no_headers_returns_none():
    # Table with no recognisable group headers → fall back to positional
    table = [
        ["Currency", "Code", "Buy", "Sell", "Buy", "Sell"],
        ["USD", "11.38", "12.22", "11.38", "11.75"],
    ]
    assert _detect_col_map(table) is None


def test_extract_rates_from_row_absa_with_col_map():
    col_map = {2: "tts_buying", 3: "tts_selling", 4: "cash_buying", 5: "cash_selling"}
    row = ["U.S. DOLLAR", "USD", "11.3500", "11.7500", "11.3500", "12.1700"]
    result = _extract_rates_from_row(row, "USD", col_map)
    assert result is not None
    assert result["tts_buying"] == 11.35
    assert result["tts_selling"] == 11.75
    assert result["cash_buying"] == 11.35
    assert result["cash_selling"] == 12.17


def test_extract_rates_from_text_absa_order():
    # Absa text: TRANSFER columns precede CASH columns
    text = (
        "ABSA BANK GHANA LIMITED\n"
        "DAILY FOREX RATES - 28 MAY 2026\n"
        "CURRENCY CODE TRANSFER BUY TRANSFER SELL CASH BUY CASH SELL\n"
        "U.S. DOLLAR USD 11.3500 11.7500 11.3500 12.1700\n"
    )
    result = _extract_rates_from_text(text, "USD")
    assert result is not None
    assert result["tts_buying"] == 11.35
    assert result["tts_selling"] == 11.75
    assert result["cash_buying"] == 11.35
    assert result["cash_selling"] == 12.17
