"""Golden-file tests on the accountant's real May 2026 data.

The data contains client and personal details, so it is not part of the repo.
Point VATTOOL_FIXTURES at the folder that holds turisti/ and vies/, e.g.
    VATTOOL_FIXTURES="/mnt/c/Users/Tony/Desktop/doema ov" pytest
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from main import run_vattool

FIXTURES = Path(os.environ.get("VATTOOL_FIXTURES", "/nonexistent"))
TURISTI = FIXTURES / "turisti" / "Ab" / "BG208113030" / "2026-05_run001"
VIES = FIXTURES / "vies" / "vies" / "BG205898840" / "2026-05_run001"

pytestmark = pytest.mark.skipif(not FIXTURES.is_dir(), reason="VATTOOL_FIXTURES not set")


def _put(line: str, start: int, width: int, value: str) -> str:
    patched = line[:start] + value.rjust(width) + line[start + width :]
    assert len(patched) == len(line)
    return patched


def test_turisti_deklar_has_cells_14_and_16(tmp_path):
    # v0.0.2 output with the two cells the accountant corrected by hand.
    expected = (TURISTI / "deklar.txt").read_bytes().decode("cp1251")

    output_dir, _ = run_vattool(
        input_csv=str(TURISTI / "input_original.csv"),
        output_root=str(tmp_path),
        submitter_person=expected[71:121].strip(),  # EGN + name, as entered in his run
    )

    expected = _put(expected, 286, 15, "5529.65")  # кл.14
    expected = _put(expected, 316, 15, "233731.23")  # кл.16

    assert (Path(output_dir) / "deklar.txt").read_bytes().decode("cp1251") == expected


def test_vies_matches_file_accepted_by_nap(tmp_path):
    accepted = (VIES / "vies_opraven.txt").read_bytes().decode("cp1251").split("\r\n")
    submitter_egn = accepted[1][3:18].strip()

    output_dir, _ = run_vattool(
        input_csv=str(VIES / "input_original.csv"),
        output_root=str(tmp_path),
        submitter_egn=submitter_egn,
    )
    produced = (Path(output_dir) / "vies.txt").read_bytes().decode("cp1251").split("\r\n")

    assert [len(line) for line in produced] == [len(line) for line in accepted]
    assert produced[0] == accepted[0]  # VHR
    assert produced[1][:18] == accepted[1][:18]  # VDR up to the EGN
    assert produced[2][:18] == accepted[2][:18]  # VTR up to the company VAT
    assert produced[3:] == accepted[3:]  # TTR, VIR, CHR
    # Submitter name and addresses in VDR/VTR wait for the per-company profile.
