from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

LEDGER_HEADER = [
    "move_id/.id",
    "company_id",
    "company_id/vat",
    "partner_id",
    "partner_id/vat",
    "tax_tag_ids",
    "balance",
    "date",
    "journal_id/type",
    "ref",
    "move_name",
    "move_id/l10n_bg_document_type",
    "invoice_date",
]

# (move id, partner, partner VAT, tag, balance, journal type, number)
# Made-up data covering every deklar cell the tool fills, a VIES customer with two
# invoices, names that cp1251 cannot hold and one document with an unmapped tag.
LEDGER_LINES = [
    ("1", "Client A", "BG222", "11", "-100", "Sale", "INV/1"),
    ("1", "Client A", "BG222", "21", "-20", "Sale", "INV/1"),
    ("2", "Client B", "BG333", "13", "-50", "Sale", "INV/2"),
    ("2", "Client B", "BG333", "24", "-4.5", "Sale", "INV/2"),
    ("3", "Ticket buyer", "", "14", "-300", "Sale", "INV/3"),
    ("4", "Tour client", "", "16", "-400", "Sale", "INV/4"),
    ("5", "Wizz Air Hungary Légiközlekedési Zrt.", "FR111", "17", "-1500", "Sale", "INV/5"),
    ("6", "Wizz Air Hungary Légiközlekedési Zrt.", "FR111", "17", "-3000", "Sale", "INV/6"),
    ("7", "Müller GmbH", "DE123", "15", "-250", "Sale", "INV/7"),
    ("8", "Supplier C", "BG444", "31", "200", "Purchase", "BILL/1"),
    ("8", "Supplier C", "BG444", "41", "40", "Purchase", "BILL/1"),
    ("9", "Søren Ærø ApS", "DK999", "32", "100", "Purchase", "BILL/2"),
    ("9", "Søren Ærø ApS", "DK999", "42", "20", "Purchase", "BILL/2"),
    ("10", "Unmapped supplier", "BG555", "99", "70", "Purchase", "BILL/3"),
]


def write_ledger(path: Path, lines=LEDGER_LINES, encoding: str = "utf-8") -> Path:
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(LEDGER_HEADER)
        for move_id, partner, vat, tag, balance, journal, number in lines:
            writer.writerow(
                [
                    move_id,
                    "Firma OOD",
                    "BG111",
                    partner,
                    vat,
                    tag,
                    balance,
                    "2026-05-10",
                    journal,
                    number if journal == "Purchase" else "",
                    number,
                    "01 - Invoice",
                    "10/05/2026",
                ]
            )
    return path


@pytest.fixture
def ledger_csv(tmp_path: Path) -> Path:
    return write_ledger(tmp_path / "ledger.csv")
