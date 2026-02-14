from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd


_LAST_NORMALIZED_DF: pd.DataFrame | None = None


@dataclass(slots=True)
class LedgerLoadResult:
    df: pd.DataFrame
    company_vat: str
    tax_periods: list[str]
    warnings: list[str]


def read_ledger_csv(path: str) -> pd.DataFrame:
    """Read a ledger CSV while preserving exact column names."""
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )


def normalize_ledger(
    df: pd.DataFrame,
    ledger_columns: dict[str, Any],
    date_mode: str,
    date_format: str | None,
) -> LedgerLoadResult:
    warnings: list[str] = []

    required = [
        "company_vat",
        "counterparty_vat",
        "document_type",
        "document_number",
        "document_date",
        "balance",
        "tax_tag_ids",
    ]
    missing_mappings = [key for key in required if not isinstance(ledger_columns.get(key), str)]
    if missing_mappings:
        raise ValueError(
            "ledger_columns is missing required mapping(s): " + ", ".join(missing_mappings)
        )

    tax_period_mapping = ledger_columns.get("tax_period") or ledger_columns.get("tax_period_source_date")
    if not isinstance(tax_period_mapping, str):
        raise ValueError("ledger_columns must define either 'tax_period' or 'tax_period_source_date'.")

    company_vat_col = ledger_columns["company_vat"]
    if company_vat_col not in df.columns:
        raise ValueError(f"Required column for company VAT is missing: '{company_vat_col}'.")

    company_vat = _first_non_blank(df[company_vat_col])
    if not company_vat:
        raise ValueError(
            f"Required column '{company_vat_col}' is present but all values are blank for company VAT."
        )

    out_df = df.copy()

    tags_col = ledger_columns["tax_tag_ids"]
    out_df["_tax_tags"] = (
        out_df[tags_col].map(_parse_tax_tags) if tags_col in out_df.columns else [[] for _ in range(len(out_df))]
    )

    balance_col = ledger_columns["balance"]
    out_df["_balance"] = (
        out_df[balance_col].map(_parse_balance)
        if balance_col in out_df.columns
        else pd.Series([None] * len(out_df), index=out_df.index)
    )

    document_date_col = ledger_columns["document_date"]
    if document_date_col not in out_df.columns:
        raise ValueError(f"Required date column is missing: '{document_date_col}'.")
    out_df["_document_date"] = _parse_date_column(
        out_df[document_date_col],
        date_mode=date_mode,
        date_format=date_format,
        column_name=document_date_col,
    )

    if tax_period_mapping not in out_df.columns:
        raise ValueError(f"Required tax period source date column is missing: '{tax_period_mapping}'.")
    out_df["_tax_period_date"] = _parse_date_column(
        out_df[tax_period_mapping],
        date_mode=date_mode,
        date_format=date_format,
        column_name=tax_period_mapping,
    )

    tax_periods = sorted({d.strftime("%Y-%m") for d in out_df["_tax_period_date"]})

    global _LAST_NORMALIZED_DF
    _LAST_NORMALIZED_DF = out_df

    return LedgerLoadResult(
        df=out_df,
        company_vat=company_vat,
        tax_periods=tax_periods,
        warnings=warnings,
    )


def write_input_copies(original_path: str, output_folder: str) -> tuple[str, str]:
    """Write raw and normalized input copies to output_folder."""
    output_dir = Path(output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)

    original_copy = output_dir / "input_original.csv"
    normalized_copy = output_dir / "input_normalized.csv"

    shutil.copyfile(original_path, original_copy)

    df_to_write = _LAST_NORMALIZED_DF if _LAST_NORMALIZED_DF is not None else read_ledger_csv(original_path)
    df_to_write.to_csv(
        normalized_copy,
        index=False,
        encoding="utf-8",
        sep=",",
        lineterminator="\r\n",
        quoting=csv.QUOTE_MINIMAL,
    )

    return str(original_copy), str(normalized_copy)


def _first_non_blank(series: pd.Series) -> str:
    for value in series.tolist():
        text = str(value).strip()
        if text:
            return text
    return ""


def _parse_tax_tags(value: Any) -> list[str]:
    text = str(value).strip()
    if not text:
        return []

    tags = [tag.strip() for tag in text.split(",")]
    return sorted(tag for tag in tags if tag)


def _parse_balance(value: Any) -> Decimal | None:
    text = str(value).strip().replace(" ", "")
    if not text:
        return None

    if "," in text and "." not in text:
        text = text.replace(",", ".")

    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid balance value: '{value}'") from exc


def _parse_date_column(
    series: pd.Series,
    date_mode: str,
    date_format: str | None,
    column_name: str,
) -> list[date]:
    if date_mode not in {"auto", "explicit"}:
        raise ValueError("date_mode must be either 'auto' or 'explicit'.")
    if date_mode == "explicit" and not date_format:
        raise ValueError("date_format must be provided when date_mode is 'explicit'.")

    parsed_values: list[date] = []
    bad_values: list[str] = []

    for raw in series.tolist():
        raw_text = str(raw).strip()
        parsed = _parse_one_date(raw_text, date_mode, date_format)
        if parsed is None:
            if raw_text not in bad_values:
                bad_values.append(raw_text)
            if len(bad_values) >= 3:
                break
        else:
            parsed_values.append(parsed)

    if bad_values:
        examples = ", ".join(repr(v) for v in bad_values)
        raise ValueError(
            f"Unable to parse date values in column '{column_name}'. "
            f"First offending value(s): {examples}."
        )

    return parsed_values


def _parse_one_date(raw: str, date_mode: str, date_format: str | None) -> date | None:
    if not raw:
        return None

    if date_mode == "explicit":
        return _try_format(raw, date_format)

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"):
        parsed = _try_format(raw, fmt)
        if parsed is not None:
            return parsed
    return None


def _try_format(raw: str, fmt: str | None) -> date | None:
    if not fmt:
        return None

    try:
        return datetime.strptime(raw, fmt).date()
    except ValueError:
        return None
