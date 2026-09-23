from decimal import Decimal

import pytest

from core.ledger import _parse_balance, read_ledger_csv
from tests.conftest import LEDGER_LINES, write_ledger


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("140.0", "140.0"),
        ("-1500", "-1500"),
        ("233,69", "233.69"),
        ("1,234.56", "1234.56"),
        ("1.234,56", "1234.56"),
        ("1 234,56", "1234.56"),
        ("1,234,567", "1234567"),
        ("1.234.567", "1234567"),
    ],
)
def test_parse_balance(raw, expected):
    assert _parse_balance(raw) == Decimal(expected)


def test_parse_balance_rejects_text():
    with pytest.raises(ValueError):
        _parse_balance("abc")


def test_reads_utf8(ledger_csv):
    df, warnings = read_ledger_csv(str(ledger_csv))
    assert len(df) == len(LEDGER_LINES)
    assert warnings == []
    assert "Søren Ærø ApS" in df["partner_id"].tolist()


def test_excel_style_cp1251_file_is_read_with_warning(tmp_path):
    lines = [("1", "Клиент ЕООД", "BG222", "11", "-100", "Sale", "INV/1")]
    path = write_ledger(tmp_path / "ansi.csv", lines, encoding="cp1251")

    df, warnings = read_ledger_csv(str(path))

    assert df["partner_id"].tolist() == ["Клиент ЕООД"]
    assert len(warnings) == 1 and "Windows-1251" in warnings[0]


def test_bad_byte_in_the_middle_loses_no_rows(ledger_csv):
    raw = ledger_csv.read_bytes()
    middle = raw.index(b"Client B")
    ledger_csv.write_bytes(raw[:middle] + b"\xff" + raw[middle:])

    df, warnings = read_ledger_csv(str(ledger_csv))

    assert len(df) == len(LEDGER_LINES)
    assert warnings
