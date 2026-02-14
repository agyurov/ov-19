from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
from typing import Any

import pandas as pd

from core.models import MappingResult


@dataclass(slots=True)
class _Target:
    table: str
    amount_column: str
    sign: int


def map_ledger_to_tax_tables(
    df: pd.DataFrame,
    tax_grid_mapping: dict[str, Any],
    ledger_columns: dict[str, Any],
    schema_by_table: dict[str, dict[str, Any]],
) -> MappingResult:
    tags_mapping = tax_grid_mapping.get("tags", {})

    pokupki_rows: list[dict[str, Any]] = []
    prodagbi_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    for row_index, row in df.iterrows():
        tags = _as_tag_list(row.get("_tax_tags"))
        if not tags:
            continue

        balance = _as_decimal(row.get("_balance"))
        if balance is None:
            continue

        known_tags = [tag for tag in tags if tag in tags_mapping]
        unknown_tags = sorted({tag for tag in tags if tag not in tags_mapping})

        if not known_tags:
            continue

        if unknown_tags:
            warnings.append(f"Row {row_index}: unknown tags: {unknown_tags}")

        row_accumulators: dict[str, dict[str, Decimal]] = {"pokupki": {}, "prodagbi": {}}
        written_by: dict[tuple[str, str], str] = {}

        for tag in known_tags:
            targets = _parse_targets(tags_mapping[tag].get("targets", []))
            for target in targets:
                key = (target.table, target.amount_column)
                if key in written_by:
                    previous_tag = written_by[key]
                    document_number = _as_text(row.get(ledger_columns.get("document_number", "")))
                    raise ValueError(
                        "Collision in row "
                        f"{row_index} (document_number={document_number}): "
                        f"tags involved: [{previous_tag}, {tag}], "
                        f"conflicting column: {target.table}.{target.amount_column}"
                    )

                written_by[key] = tag
                amount = balance if target.sign == 1 else -balance
                row_accumulators[target.table][target.amount_column] = amount

        if row_accumulators["pokupki"]:
            pokupki_rows.append(
                _build_output_row(
                    table_name="pokupki",
                    schema=schema_by_table["pokupki"],
                    source_row=row,
                    row_index=row_index,
                    ledger_columns=ledger_columns,
                    amount_values=row_accumulators["pokupki"],
                    warnings=warnings,
                )
            )

        if row_accumulators["prodagbi"]:
            prodagbi_rows.append(
                _build_output_row(
                    table_name="prodagbi",
                    schema=schema_by_table["prodagbi"],
                    source_row=row,
                    row_index=row_index,
                    ledger_columns=ledger_columns,
                    amount_values=row_accumulators["prodagbi"],
                    warnings=warnings,
                )
            )

    return MappingResult(
        pokupki_rows=pokupki_rows,
        prodagbi_rows=prodagbi_rows,
        warnings=warnings,
    )


def _build_output_row(
    table_name: str,
    schema: dict[str, Any],
    source_row: pd.Series,
    row_index: Any,
    ledger_columns: dict[str, Any],
    amount_values: dict[str, Decimal],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    output = _schema_defaults(schema)

    output["vat_number"] = _as_text(source_row.get(ledger_columns.get("company_vat", "")))

    tax_period_date = source_row.get("_tax_period_date")
    output["tax_period"] = (
        tax_period_date.strftime("%Y%m") if isinstance(tax_period_date, date) else ""
    )

    raw_document_type = source_row.get(ledger_columns.get("document_type", ""))
    raw_document_type_text = _as_text(raw_document_type)
    normalized_document_type = _normalize_document_type(raw_document_type)
    output["document_type"] = normalized_document_type

    if warnings is not None and not re.match(r"^(\d{2})", raw_document_type_text):
        warnings.append(f"Row {row_index}: unrecognized document_type '{raw_document_type}'")

    output["document_number"] = _resolve_document_number(
        source_row=source_row,
        table_name=table_name,
        ledger_columns=ledger_columns,
    )

    document_date = source_row.get("_document_date")
    output["document_date"] = document_date.isoformat() if isinstance(document_date, date) else ""

    output["counterparty_vat"] = _as_text(source_row.get(ledger_columns.get("counterparty_vat", "")))

    counterparty_name_column = ledger_columns.get("partner_name")
    output["counterparty_name"] = _as_text(source_row.get(counterparty_name_column or ""))

    for amount_column, value in amount_values.items():
        output[amount_column] = value

    return output


def _resolve_document_number(
    source_row: pd.Series,
    table_name: str,
    ledger_columns: dict[str, Any],
) -> str:
    # Odoo can store purchase numbers in `ref` and sales numbers in `move_name`,
    # so we resolve per tax table while keeping a shared output field name.
    if table_name == "pokupki":
        candidates = (
            "purchase_doc_number",
            "purchase_ref",
            "document_number",
            "sales_move_name",
        )
    elif table_name == "prodagbi":
        candidates = (
            "sales_doc_number",
            "document_number",
            "sales_move_name",
            "purchase_ref",
        )
    else:
        candidates = ("document_number", "sales_move_name", "purchase_ref")

    for key in candidates:
        column_name = ledger_columns.get(key)
        if isinstance(column_name, str) and column_name.strip():
            value = _as_text(source_row.get(column_name))
            if value:
                return value

    return ""


def _schema_defaults(schema: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in schema.get("fields", []):
        name = field.get("internal_name")
        if not isinstance(name, str) or not name:
            continue

        if field.get("type") == "float64":
            out[name] = Decimal("0")
        else:
            out[name] = ""

    return out


def _parse_targets(raw_targets: list[dict[str, Any]]) -> list[_Target]:
    targets: list[_Target] = []
    for target in raw_targets:
        table = target.get("table")
        amount_column = target.get("amount_column")
        sign = target.get("sign", 1)
        if table not in {"pokupki", "prodagbi"}:
            continue
        if not isinstance(amount_column, str) or not amount_column:
            continue
        if sign not in {1, -1}:
            raise ValueError(f"Invalid target sign {sign!r} for {table}.{amount_column}")

        targets.append(_Target(table=table, amount_column=amount_column, sign=sign))
    return targets


def _as_tag_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(tag) for tag in value if str(tag)]
    return []


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_document_type(value: Any) -> str:
    text = _as_text(value)
    if not text:
        return ""

    match = re.match(r"^(\d{2})", text)
    if match:
        return match.group(1)

    return text
