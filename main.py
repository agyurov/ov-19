from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from core.config_loader import ConfigError, load_all_configs
from core.deklar import build_deklar_row
from core.ledger import normalize_ledger, read_ledger_csv
from core.mapping import map_ledger_to_tax_tables
from core.vies import build_vies_data, write_vies_csv, write_vies_txt
from core.version import APP_VERSION
from core.writer import (
    write_csv_tables,
    write_deklar_csv,
    write_deklar_txt,
    write_txt_tables,
)


def make_run_dir(output_root: str, company_vat: str, tax_period: str) -> Path:
    vat_dir = Path(output_root) / (company_vat or "unknown_vat")
    vat_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{tax_period}_run"
    highest = 0
    for child in vat_dir.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if not name.startswith(prefix):
            continue

        suffix = name[len(prefix) :]
        if len(suffix) == 3 and suffix.isdigit():
            highest = max(highest, int(suffix))

    run_dir = vat_dir / f"{prefix}{highest + 1:03d}"
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_dir


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the VATTool pipeline.")
    parser.add_argument("--input", required=True, help="Path to input ledger CSV.")
    parser.add_argument("--output-root", default="vattool_19", help="Root output folder.")
    parser.add_argument(
        "--date-mode",
        choices=["auto", "explicit"],
        default="auto",
        help="Date parsing mode for ledger dates.",
    )
    parser.add_argument(
        "--date-format",
        default=None,
        help="Date format for explicit date mode (for example %%d.%%m.%%Y).",
    )
    parser.add_argument(
        "--submitter-person",
        default="",
        help="Submitter person value used in deklar data.",
    )
    parser.add_argument(
        "--submitter-egn",
        default="",
        help="Submitter EGN value stored in run summary.",
    )
    return parser


def run_vattool(
    input_csv: str,
    output_root: str,
    submitter_person: str = "",
    submitter_egn: str = "",
    date_mode: str = "auto",
    date_format: str | None = None,
) -> tuple[str, int]:
    base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    config_dir = base_dir / "configs"

    configs = load_all_configs(str(config_dir))

    schemas = configs["schemas"]
    ledger_columns = configs["mappings"]["ledger_columns"]
    tax_grid_mapping = configs["mappings"]["tax_grid"]
    deklar_aggregation = configs["deklar_aggregation"]

    df = read_ledger_csv(input_csv)
    ledger_result = normalize_ledger(df, ledger_columns, date_mode, date_format)

    if len(ledger_result.tax_periods) != 1:
        raise ValueError(
            "Input ledger must contain exactly one tax period; "
            f"found {len(ledger_result.tax_periods)}: {ledger_result.tax_periods}"
        )

    mapping_result = map_ledger_to_tax_tables(
        ledger_result.df,
        tax_grid_mapping,
        ledger_columns,
        schemas,
    )

    taxpayer_name = ""
    company_name_column = ledger_columns.get("company_name")
    if isinstance(company_name_column, str) and company_name_column in ledger_result.df.columns:
        for value in ledger_result.df[company_name_column].tolist():
            text = str(value).strip()
            if text:
                taxpayer_name = text
                break

    deklar_row, deklar_warnings = build_deklar_row(
        mapping_result.pokupki_rows,
        mapping_result.prodagbi_rows,
        schemas,
        deklar_aggregation,
        taxpayer_name=taxpayer_name,
        submitter_person=submitter_person,
    )

    tax_period = ledger_result.tax_periods[0]
    year, month = tax_period.split("-", 1)
    reporting_period = f"{month}/{year}"

    vies_data = build_vies_data(
        mapping_result.prodagbi_rows,
        reporting_period=reporting_period,
        declarer_id="",
        declarer_name=submitter_person,
        registered_vat=ledger_result.company_vat,
        registered_name=taxpayer_name,
        registered_address="",
    )

    run_dir = make_run_dir(output_root, ledger_result.company_vat, tax_period)
    shutil.copyfile(input_csv, run_dir / "input_original.csv")

    write_csv_tables(mapping_result.pokupki_rows, mapping_result.prodagbi_rows, schemas, run_dir)
    _, txt_warnings = write_txt_tables(mapping_result.pokupki_rows, mapping_result.prodagbi_rows, schemas, run_dir)
    write_deklar_csv(deklar_row, schemas, run_dir)
    _, deklar_txt_warnings = write_deklar_txt(deklar_row, schemas, run_dir)
    write_vies_csv(vies_data, run_dir)
    write_vies_txt(vies_data, schemas["vies"], run_dir)

    all_warnings = [
        *mapping_result.warnings,
        *txt_warnings,
        *deklar_warnings,
        *deklar_txt_warnings,
    ]

    summary_lines = [
        f"app_version: {APP_VERSION}",
        f"company_vat: {ledger_result.company_vat}",
        f"tax_period: {tax_period}",
        f"submitter_person: {submitter_person}",
        f"submitter_egn: {submitter_egn}",
        f"ledger_row_count: {len(ledger_result.df)}",
        f"pokupki_row_count: {len(mapping_result.pokupki_rows)}",
        f"prodagbi_row_count: {len(mapping_result.prodagbi_rows)}",
        f"vies_vir_count: {len(vies_data.get('VIR', []))}",
        f"warnings_count: {len(all_warnings)}",
        "warnings_first_50:",
    ]
    summary_lines.extend(f"- {warning}" for warning in all_warnings[:50])
    (run_dir / "run_summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return str(run_dir), len(all_warnings)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        output_dir, warnings_count = run_vattool(
            input_csv=args.input,
            output_root=args.output_root,
            submitter_person=args.submitter_person,
            submitter_egn=args.submitter_egn,
            date_mode=args.date_mode,
            date_format=args.date_format,
        )

        print(f"OUTPUT DIR: {output_dir}")
        print(f"WARNINGS: {warnings_count}")
        return 0
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"RUNTIME ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
