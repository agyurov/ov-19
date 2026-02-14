from __future__ import annotations

from decimal import Decimal
from typing import Any


def build_deklar_row(
    pokupki_rows: list[dict],
    prodagbi_rows: list[dict],
    schemas: dict,
    deklar_aggregation: dict,
    taxpayer_name: str | None = None,
    submitter_person: str | None = None,
) -> tuple[dict, list[str]]:
    deklar_schema = schemas.get("deklar")
    if not isinstance(deklar_schema, dict):
        raise ValueError("Missing or invalid 'deklar' schema in schemas")

    fields = deklar_schema.get("fields")
    if not isinstance(fields, list):
        raise ValueError("Deklar schema 'fields' must be a list")

    deklar_row: dict[str, Any] = {}
    warnings: list[str] = []

    for field in fields:
        if not isinstance(field, dict):
            continue

        internal_name = field.get("internal_name")
        if not isinstance(internal_name, str) or not internal_name:
            continue

        field_type = str(field.get("type") or "").lower()
        if field_type in {"float64", "int64"}:
            deklar_row[internal_name] = Decimal("0")
        else:
            deklar_row[internal_name] = ""

    _set_if_present(deklar_row, "vat_number", _first_available_value("vat_number", pokupki_rows, prodagbi_rows))
    _set_if_present(deklar_row, "tax_period", _first_available_value("tax_period", pokupki_rows, prodagbi_rows))
    _set_if_present(deklar_row, "branch_number", "0")

    if taxpayer_name is not None:
        taxpayer_name = taxpayer_name.strip()
        if taxpayer_name:
            _set_if_present(deklar_row, "taxpayer_name", taxpayer_name)
    if submitter_person is not None:
        submitter_person = submitter_person.strip()
        if submitter_person:
            _set_if_present(deklar_row, "submitter_person", submitter_person)

    rules = deklar_aggregation.get("field_rules") if isinstance(deklar_aggregation, dict) else None
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue

            target_field = rule.get("target_field")
            expression = rule.get("expression")
            if not isinstance(target_field, str) or not isinstance(expression, dict):
                continue

            deklar_row[target_field] = _evaluate_expression(expression, pokupki_rows, prodagbi_rows)

    document_count_rules = deklar_aggregation.get("document_count_rules", {}) if isinstance(deklar_aggregation, dict) else {}
    if isinstance(document_count_rules, dict):
        for target_field, rule in document_count_rules.items():
            if not isinstance(target_field, str) or not isinstance(rule, dict):
                continue

            source_table = rule.get("source_table")
            distinct_key_fields = rule.get("distinct_key_fields")
            if not isinstance(source_table, str) or not isinstance(distinct_key_fields, list):
                continue

            if source_table == "prodagbi":
                rows = prodagbi_rows
            elif source_table == "pokupki":
                rows = pokupki_rows
            else:
                warnings.append(
                    f"document_count_rules[{target_field}] references unknown source_table '{source_table}'"
                )
                continue

            distinct_documents: set[tuple[str, ...]] = set()
            for row in rows:
                if not isinstance(row, dict):
                    continue

                key: list[str] = []
                for field_name in distinct_key_fields:
                    if not isinstance(field_name, str):
                        key.append("")
                        continue

                    value = row.get(field_name)
                    key.append("" if value is None else str(value))

                distinct_documents.add(tuple(key))

            deklar_row[target_field] = Decimal(len(distinct_documents))

    # compute deklar sales totals from prodagbi totals
    sales_total_tax_base = Decimal("0")
    sales_total_vat = Decimal("0")
    for row in prodagbi_rows:
        if not isinstance(row, dict):
            continue
        sales_total_tax_base += _to_decimal(row.get("total_tax_base"))
        sales_total_vat += _to_decimal(row.get("total_vat"))

    if "sales_total_tax_base" in deklar_row:
        deklar_row["sales_total_tax_base"] = sales_total_tax_base
    if "sales_total_vat" in deklar_row:
        deklar_row["sales_total_vat"] = sales_total_vat

    if "vat_due" in deklar_row and "vat_refundable" in deklar_row:
        delta = _to_decimal(deklar_row.get("sales_total_vat")) - _to_decimal(deklar_row.get("total_tax_credit"))
        deklar_row["vat_due"] = max(delta, Decimal("0"))
        deklar_row["vat_refundable"] = -min(delta, Decimal("0"))
        if delta != Decimal("0"):
            warnings.append(
                "vat_due/vat_refundable recalculated from sales_total_vat - total_tax_credit"
            )

    return deklar_row, warnings


def _evaluate_expression(expression: dict[str, Any], pokupki_rows: list[dict], prodagbi_rows: list[dict]) -> Decimal:
    op = expression.get("op")
    if op == "sum":
        sources = expression.get("sources")
        if not isinstance(sources, list):
            return Decimal("0")

        total = Decimal("0")
        for source in sources:
            if not isinstance(source, dict):
                continue

            table = source.get("table")
            field = source.get("field")
            if not isinstance(table, str) or not isinstance(field, str):
                continue

            rows = pokupki_rows if table == "pokupki" else prodagbi_rows if table == "prodagbi" else []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                total += _to_decimal(row.get(field))

        return total

    if op == "subtract":
        left = expression.get("left")
        right = expression.get("right")
        left_value = _evaluate_expression(left, pokupki_rows, prodagbi_rows) if isinstance(left, dict) else Decimal("0")
        right_value = (
            _evaluate_expression(right, pokupki_rows, prodagbi_rows) if isinstance(right, dict) else Decimal("0")
        )
        return left_value - right_value

    return Decimal("0")


def _first_available_value(field_name: str, pokupki_rows: list[dict], prodagbi_rows: list[dict]) -> Any:
    for rows in (pokupki_rows, prodagbi_rows):
        for row in rows:
            if not isinstance(row, dict):
                continue
            value = row.get(field_name)
            if value not in (None, ""):
                return value
    return ""


def _set_if_present(target: dict[str, Any], field_name: str, value: Any) -> None:
    if field_name in target:
        target[field_name] = value


def _to_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
