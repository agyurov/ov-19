from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

import pytest

import main
from main import run_vattool
from tests.conftest import PROJECT_DIR

SCHEMAS = {
    name: json.loads((PROJECT_DIR / "configs" / "schemas" / f"{name}-schema.json").read_text(encoding="utf-8"))
    for name in ("pokupki", "prodagbi", "deklar", "vies")
}
DEKLAR_FIELDS = {field["internal_name"]: field for field in SCHEMAS["deklar"]["fields"]}

# deklar cell -> the ledger columns it must equal the sum of
DEKLAR_SOURCES = {
    "sales_base_20": [("prodagbi", "base_20")],
    "sales_vat_20": [("prodagbi", "vat_20")],
    "sales_base_intra_community_acq": [
        ("prodagbi", "base_intra_community_acq"),
        ("prodagbi", "base_reverse_charge_82"),
    ],
    "sales_vat_intra_community_and_82": [("prodagbi", "vat_intra_community_and_82")],
    "sales_vat_private_use": [("prodagbi", "vat_for_private_use")],
    "sales_base_9": [("prodagbi", "base_9")],
    "sales_vat_9": [("prodagbi", "vat_9")],
    "sales_base_0_chapter3": [("prodagbi", "base_0_chapter3")],
    "sales_base_0_intra_community_supply": [("prodagbi", "base_0_intra_community_supply")],
    "sales_base_0_other": [("prodagbi", "base_0_other")],
    "sales_base_services_21_2": [("prodagbi", "base_services_21_2")],
    "sales_base_69_2_eu": [("prodagbi", "base_69_2_eu")],
    "sales_base_exempt": [("prodagbi", "base_exempt")],
    "purchases_base_and_vat_no_credit": [("pokupki", "base_and_vat_no_credit")],
    "purchases_base_full_credit": [("pokupki", "base_full_credit")],
    "purchases_vat_full_credit": [("pokupki", "vat_full_credit")],
    "purchases_base_partial_credit": [("pokupki", "base_partial_credit")],
    "purchases_vat_partial_credit": [("pokupki", "vat_partial_credit")],
    "sales_total_tax_base": [("prodagbi", "total_tax_base")],
    "sales_total_vat": [("prodagbi", "total_vat")],
}


@pytest.fixture
def run_dir(ledger_csv: Path, tmp_path: Path) -> Path:
    output_dir, _ = run_vattool(
        input_csv=str(ledger_csv),
        output_root=str(tmp_path / "out"),
        submitter_person="Test Person",
        submitter_egn="0000000000",
    )
    return Path(output_dir)


def _column_sum(run_dir: Path, table: str, column: str) -> Decimal:
    with (run_dir / f"{table}.csv").open(encoding="utf-8") as handle:
        return sum((Decimal(row[column] or "0") for row in csv.DictReader(handle)), Decimal("0"))


def _deklar_cell(line: str, name: str) -> Decimal:
    field = DEKLAR_FIELDS[name]
    start = field["start_pos"] - 1
    return Decimal(line[start : start + field["length"]].strip())


def _deklar_line(run_dir: Path) -> str:
    return (run_dir / "deklar.txt").read_bytes().decode("cp1251").rstrip("\r\n")


@pytest.mark.parametrize("cell", sorted(DEKLAR_SOURCES))
def test_every_deklar_cell_equals_its_ledger_columns(run_dir, cell):
    expected = sum(_column_sum(run_dir, table, column) for table, column in DEKLAR_SOURCES[cell])
    assert _deklar_cell(_deklar_line(run_dir), cell) == expected


def test_deklar_cells_14_and_16_are_filled(run_dir):
    line = _deklar_line(run_dir)
    assert line[286:301].strip() == "300.00"  # кл.14
    assert line[316:331].strip() == "400.00"  # кл.16


def test_txt_files_are_cp1251_with_fixed_line_lengths(run_dir):
    for table in ("pokupki", "prodagbi", "deklar"):
        raw = (run_dir / f"{table}.txt").read_bytes()
        lines = raw.decode("cp1251").split("\r\n")
        assert lines[-1] == ""  # these files end with CRLF
        assert {len(line) for line in lines[:-1]} == {SCHEMAS[table]["line_length"]}


def test_names_are_transliterated_in_txt_but_kept_in_csv(run_dir):
    pokupki_txt = (run_dir / "pokupki.txt").read_bytes().decode("cp1251")
    pokupki_csv = (run_dir / "pokupki.csv").read_text(encoding="utf-8")
    prodagbi_txt = (run_dir / "prodagbi.txt").read_bytes().decode("cp1251")

    assert "Soren AEro ApS" in pokupki_txt
    assert "Søren Ærø ApS" in pokupki_csv
    assert "Wizz Air Hungary Legikozlekedesi Zrt." in prodagbi_txt

    summary = (run_dir / "run_summary.txt").read_text(encoding="utf-8")
    assert "'Søren Ærø ApS' -> 'Soren AEro ApS'" in summary


def test_document_with_only_unknown_tags_is_reported(run_dir):
    summary = (run_dir / "run_summary.txt").read_text(encoding="utf-8")
    assert "BILL/3" in summary and "SKIPPED" in summary
    assert "BILL/3" not in (run_dir / "pokupki.csv").read_text(encoding="utf-8")


def test_summary_has_new_version_and_no_recalculation_noise(run_dir):
    summary = (run_dir / "run_summary.txt").read_text(encoding="utf-8")
    assert "app_version: 0.0.3" in summary
    assert "recalculated" not in summary


def test_vies_record_order_widths_and_ending(run_dir):
    raw = (run_dir / "vies.txt").read_bytes()
    assert not raw.endswith(b"\r\n")

    lines = raw.decode("cp1251").split("\r\n")
    assert [(line[:3], len(line)) for line in lines] == [
        ("VHR", 15),
        ("VDR", 373),
        ("VTR", 368),
        ("TTR", 27),
        ("VIR", 66),
        ("CHR", 8),
    ]
    assert lines[0] == "VHR05/2026    1"
    assert lines[1][3:18] == "0000000000     "  # submitter EGN
    assert lines[1][218:222] == "    "  # no stray 0 in the postal code
    assert lines[3] == "TTR     4500.00        0.00"
    # two invoices to the same VAT number become one VIR line
    assert lines[4] == "VIR" + "1".rjust(5) + "FR111".ljust(15) + "0.00".rjust(12) * 2 + "4500.00".rjust(12) + " " * 7
    assert lines[5] == "CHR    0"


def test_empty_vies_still_ends_with_chr(tmp_path):
    from tests.conftest import write_ledger

    ledger = write_ledger(tmp_path / "ledger.csv", [("1", "Client A", "BG222", "11", "-100", "Sale", "INV/1")])
    output_dir, _ = run_vattool(input_csv=str(ledger), output_root=str(tmp_path / "out"))

    lines = (Path(output_dir) / "vies.txt").read_bytes().decode("cp1251").split("\r\n")
    assert [line[:3] for line in lines] == ["VHR", "VDR", "VTR", "TTR", "CHR"]
    assert lines[0] == "VHR05/2026    0"
    assert lines[3] == "TTR        0.00        0.00"
    assert lines[4] == "CHR    0"


def test_failed_write_leaves_no_run_folder(ledger_csv, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(main, "write_vies_txt", fail)
    output_root = tmp_path / "out"

    with pytest.raises(OSError):
        run_vattool(input_csv=str(ledger_csv), output_root=str(output_root))

    assert list((output_root / "BG111").iterdir()) == []
