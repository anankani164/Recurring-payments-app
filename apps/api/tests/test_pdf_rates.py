import pytest

from app.pdf_rates import PdfParseError, _extract_rates_from_row, _extract_rates_from_text, _parse_date


def test_parse_date_ymd():
    parsed = _parse_date("Forex rates for 2026-05-26")
    assert parsed.isoformat() == "2026-05-26"


def test_parse_date_failure():
    with pytest.raises(PdfParseError):
        _parse_date("no date here")


def test_extract_rates_from_row():
    row = ["US Dollar", "USD", "10.10", "10.20", "10.30", "10.40"]
    parsed = _extract_rates_from_row(row, "USD")
    assert parsed is not None
    assert parsed["tts_selling"] == 10.40


def test_extract_rates_from_text_fallback():
    text = "FX SHEET\nUSD 11.11 11.22 11.33 11.44\n"
    parsed = _extract_rates_from_text(text, "USD")
    assert parsed is not None
    assert parsed["cash_buying"] == 11.11
