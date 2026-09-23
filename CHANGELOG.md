# Changelog

Developer notes for VATTool 19. The user-facing guide is `USER_GUIDE.txt`.

## 0.0.3 (2026-09-23)

Fixes from the accountant's test on real May 2026 data (turisti BG208113030 and
Рикрутив BG205898840), plus issues found in a code review. Both real inputs were
rerun: pokupki and prodagbi are byte-identical to 0.0.2, deklar changes only in
кл.14/16 for turisti, and vies.txt for Рикрутив now matches the NAP-accepted file
in every line length and in VHR, TTR, VIR and CHR.

### Fixed: deklar
- кл.13, 14, 15, 16, 23, 24, 32 and 42 were always 0.00: there were no rules for them
  in `deklar-aggregation.json`. Each is now the sum of its prodagbi/pokupki column
  (turisti: кл.14 = 5529.65, кл.16 = 233731.23).
- Removed the rules for кл.01, 20, 50 and 60 from the config. `core/deklar.py`
  always overwrote them; results are unchanged.
- Removed the "vat_due/vat_refundable recalculated" warning, which fired on almost
  every run and made "Warnings: YES" meaningless.

### Fixed: VIES (`core/vies.py`)
- Each record is written at its own width: VHR 15, VDR 373, VTR 368, TTR 27, VIR 66,
  CHR 8. Before, every line was padded to 373.
- Added the CHR record (`CHR    0`) as the last line, with no trailing CRLF, as in
  the accepted file.
- The VDR postal code no longer writes a stray `0` at column 221 (the field is now text).
- VDR now carries the submitter EGN entered in the UI (it was empty).

### Fixed: special characters and input
- Text that Windows-1251 cannot hold (é, ö, ø, æ, ß, ł, ...) crashed the run with
  `'charmap' codec can't encode character`. It is now transliterated in the .txt files
  (`core/text_encoding.py`: explicit map, then NFKD without accents, `?` as the last
  resort). This happens before truncation, so field widths stay fixed. Every change
  is listed in run_summary.txt. The .csv files keep the original text.
- An input CSV that is not UTF-8 (typically resaved from Excel) crashed the run.
  It is now read as Windows-1251, with a warning.
- Amounts such as `1,234.56` and `1.234,56` are parsed instead of stopping the run.

### Fixed: robustness and warnings
- A document whose tax tags are all missing from `tax-grid-mapping.json` was dropped
  without any warning. It now logs "SKIPPED" with the document number and partner.
  This is the most likely cause of documents missing from the 74/115 counts.
- Warnings name the document (number / partner) instead of an internal row index.
- A failure while writing files no longer leaves a half-written run folder.
- Config warnings (formerly `warnings.warn`, invisible in the exe) go to run_summary.txt.
- `document-type-mapping.json` is now applied. It was loaded but never used.

### Added
- Automatic config upgrades: program-owned configs whose bundled `config_version` is
  newer replace the installed copy on startup. The old file is kept as `*.vN.bak`,
  and the upgrade is noted in run_summary.txt. `deklar-aggregation` and the `vies`
  schema are now version 2. User-edited mappings stay at version 1 and are never
  replaced. When you change a program-owned config, bump its version here and in
  `SUPPORTED_CONFIG_VERSIONS` (`core/config_loader.py`).
- `embed_default_configs.py` regenerates `core/default_configs.py` from `configs/`.
- Tests (`pytest`): every deklar cell against its ledger sum, the VIES layout,
  transliteration, CSV encodings, amount parsing, config upgrades, and cleanup after
  a failure. `tests/test_real_fixtures.py` runs golden-file tests on the accountant's
  data when `VATTOOL_FIXTURES` points at it. That data is private and not in the repo.

### Changed
- The design spec moved from `requirements.txt` to `SPEC.txt`. `requirements.txt` now
  lists the dependencies (pandas, pyinstaller, pytest).
- USER_GUIDE.txt rewritten: short and simple.
- Removed unused code from `core/ledger.py` (`write_input_copies`, `_LAST_NORMALIZED_DF`).

### Open: waiting for the accountant
- кл.01 leaves out кл.17–19 (`TAX_BASE_COLUMNS` in `core/mapping.py`). For Рикрутив,
  кл.01 = 0.00 while кл.17 = 4500.00. Should they be included?
- кл.40 counts only кл.41. Should it be кл.41 + кл.42 × кл.33 + кл.43?
- кл.70/80 prompt on every run (his request). The validation design depends on where
  his кл.80 = 233.69 came from when the tool's кл.60 was 87.83.
- VIES: intra-EU goods (кл.15) never reach VIR; only services (кл.17) do.
- VIES header: submitter name form (NAP accepted `ЕмилияТашеваГюрова`), city, postal
  code, address, capacity and the VTR company address. The plan is a per-company
  profile. The Odoo export already has `company_id/city` and `company_id/street`.
- What the CHR count means. The accepted file has 0 with one VIR line.
- A blank `invoice_date` stops the run. Should the posting date be used instead?

### Open: other
- More than one tax period stops the run. The spec says it should only warn.
- Check on Windows whether the PyInstaller 6 build finds `configs/` next to the exe
  or puts it under `_internal/`.
- `core/validation.py` is empty and can be deleted.

## 0.0.2 (2026-02-15)

First version tested by the accountant: deklar, pokupki, prodagbi and VIES (CSV + TXT)
from an Odoo v19 ledger CSV, with a Tkinter UI and a PyInstaller build.
