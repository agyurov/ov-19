from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

SUPPORTED_CONFIG_VERSION = 1
REQUIRED_SCHEMA_FIELD_KEYS = {"internal_name", "type", "required"}
ALLOWED_SCHEMA_TABLES = {"pokupki", "prodagbi", "deklar"}


class ConfigError(Exception):
    """Raised when configuration files are invalid."""


def load_all_configs(config_root: str) -> dict[str, Any]:
    root = Path(config_root)
    if not root.exists() or not root.is_dir():
        raise ConfigError(f"Config root does not exist or is not a directory: {config_root}")

    loaded_by_type = _load_and_validate_jsons(root)

    schema_by_table = _collect_schemas(loaded_by_type)
    _validate_schema_content(schema_by_table)

    tax_grid_mapping = _get_single_config(loaded_by_type, "tax_grid_mapping")
    ledger_columns = _get_single_config(loaded_by_type, "ledger_columns")
    deklar_aggregation = _get_single_config(loaded_by_type, "deklar_aggregation")

    _validate_tax_grid_mapping(tax_grid_mapping, schema_by_table)
    _validate_ledger_columns(ledger_columns)
    _validate_deklar_aggregation(deklar_aggregation, schema_by_table)

    return {
        "schemas": schema_by_table,
        "mappings": {
            "tax_grid": tax_grid_mapping,
            "ledger_columns": ledger_columns,
        },
        "deklar_aggregation": deklar_aggregation,
    }


def _load_and_validate_jsons(root: Path) -> dict[str, list[dict[str, Any]]]:
    loaded_by_type: dict[str, list[dict[str, Any]]] = {}

    for json_path in sorted(root.rglob("*.json")):
        payload = _read_json(json_path)
        config_type = payload.get("config_type")
        config_version = payload.get("config_version")

        if not isinstance(config_type, str) or not config_type:
            raise ConfigError(
                f"{json_path}: missing/invalid required key 'config_type' (string expected)"
            )

        if not isinstance(config_version, int):
            raise ConfigError(
                f"{json_path}: missing/invalid required key 'config_version' (int expected)"
            )

        if config_version != SUPPORTED_CONFIG_VERSION:
            raise ConfigError(
                f"{json_path}: unsupported config_version={config_version}; "
                f"supported version is {SUPPORTED_CONFIG_VERSION}"
            )

        payload["_path"] = str(json_path)
        loaded_by_type.setdefault(config_type, []).append(payload)

    return loaded_by_type


def _read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}: invalid JSON ({exc.msg})") from exc

    if not isinstance(parsed, dict):
        raise ConfigError(f"{path}: top-level JSON value must be an object")
    return parsed


def _collect_schemas(loaded_by_type: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    schema_by_table: dict[str, dict[str, Any]] = {}
    for config_type, entries in loaded_by_type.items():
        if config_type not in ALLOWED_SCHEMA_TABLES:
            continue

        if len(entries) != 1:
            raise ConfigError(
                f"Expected exactly one '{config_type}' schema config, found {len(entries)}"
            )

        schema_by_table[config_type] = entries[0]

    missing = sorted(ALLOWED_SCHEMA_TABLES - schema_by_table.keys())
    if missing:
        raise ConfigError(f"Missing required schema config(s): {', '.join(missing)}")

    return schema_by_table


def _get_single_config(
    loaded_by_type: dict[str, list[dict[str, Any]]],
    config_type: str,
) -> dict[str, Any]:
    entries = loaded_by_type.get(config_type, [])
    if len(entries) != 1:
        raise ConfigError(f"Expected exactly one '{config_type}' config, found {len(entries)}")
    return entries[0]


def _validate_schema_content(schema_by_table: dict[str, dict[str, Any]]) -> None:
    for table, schema in schema_by_table.items():
        fields = schema.get("fields")
        if not isinstance(fields, list):
            raise ConfigError(f"{schema['_path']}: schema '{table}' must include a 'fields' list")

        seen_names: set[str] = set()
        for index, field in enumerate(fields):
            if not isinstance(field, dict):
                raise ConfigError(
                    f"{schema['_path']}: fields[{index}] must be an object"
                )

            missing_keys = sorted(REQUIRED_SCHEMA_FIELD_KEYS - field.keys())
            if missing_keys:
                raise ConfigError(
                    f"{schema['_path']}: field at index {index} missing required key(s): "
                    f"{', '.join(missing_keys)}"
                )

            name = field["internal_name"]
            if not isinstance(name, str) or not name:
                raise ConfigError(
                    f"{schema['_path']}: fields[{index}].internal_name must be a non-empty string"
                )

            if name in seen_names:
                raise ConfigError(
                    f"{schema['_path']}: duplicate schema field internal_name '{name}'"
                )
            seen_names.add(name)


def _schema_field_names(schema_by_table: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    table_fields: dict[str, set[str]] = {}
    for table, schema in schema_by_table.items():
        table_fields[table] = {
            field["internal_name"]
            for field in schema.get("fields", [])
            if isinstance(field, dict) and isinstance(field.get("internal_name"), str)
        }
    return table_fields


def _schema_amount_field_names(schema_by_table: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    amount_fields: dict[str, set[str]] = {}
    for table, schema in schema_by_table.items():
        amount_fields[table] = {
            field["internal_name"]
            for field in schema.get("fields", [])
            if isinstance(field, dict)
            and isinstance(field.get("internal_name"), str)
            and field.get("is_amount") is True
        }
    return amount_fields


def _validate_tax_grid_mapping(
    tax_grid_mapping: dict[str, Any],
    schema_by_table: dict[str, dict[str, Any]],
) -> None:
    tags = tax_grid_mapping.get("tags")
    if not isinstance(tags, dict):
        raise ConfigError(f"{tax_grid_mapping['_path']}: 'tags' must be an object")

    table_fields = _schema_field_names(schema_by_table)
    amount_fields = _schema_amount_field_names(schema_by_table)

    for tag_code, tag_config in tags.items():
        if not isinstance(tag_config, dict):
            raise ConfigError(
                f"{tax_grid_mapping['_path']}: tags.{tag_code} must be an object"
            )

        targets = tag_config.get("targets")
        if not isinstance(targets, list):
            raise ConfigError(
                f"{tax_grid_mapping['_path']}: tags.{tag_code}.targets must be a list"
            )

        seen_pairs: set[tuple[str, str]] = set()
        for index, target in enumerate(targets):
            if not isinstance(target, dict):
                raise ConfigError(
                    f"{tax_grid_mapping['_path']}: tags.{tag_code}.targets[{index}] must be an object"
                )

            table = target.get("table")
            amount_column = target.get("amount_column")
            if table not in {"pokupki", "prodagbi"}:
                raise ConfigError(
                    f"{tax_grid_mapping['_path']}: tags.{tag_code}.targets[{index}].table "
                    "must be 'pokupki' or 'prodagbi'"
                )
            if not isinstance(amount_column, str) or not amount_column:
                raise ConfigError(
                    f"{tax_grid_mapping['_path']}: tags.{tag_code}.targets[{index}].amount_column "
                    "must be a non-empty string"
                )

            pair = (table, amount_column)
            if pair in seen_pairs:
                raise ConfigError(
                    f"{tax_grid_mapping['_path']}: duplicate target (table={table}, "
                    f"amount_column={amount_column}) in tags.{tag_code}.targets"
                )
            seen_pairs.add(pair)

            if amount_column not in table_fields[table]:
                raise ConfigError(
                    f"{tax_grid_mapping['_path']}: tags.{tag_code}.targets[{index}] references "
                    f"unknown schema field '{amount_column}' in table '{table}'"
                )

            if amount_column not in amount_fields[table]:
                warnings.warn(
                    f"{tax_grid_mapping['_path']}: tags.{tag_code}.targets[{index}] references "
                    f"'{amount_column}' in '{table}' which is not marked is_amount=true",
                    stacklevel=2,
                )


def _validate_deklar_aggregation(
    deklar_aggregation: dict[str, Any],
    schema_by_table: dict[str, dict[str, Any]],
) -> None:
    field_rules = deklar_aggregation.get("field_rules")
    if not isinstance(field_rules, list):
        raise ConfigError(f"{deklar_aggregation['_path']}: 'field_rules' must be a list")

    table_fields = _schema_field_names(schema_by_table)
    deklar_fields = table_fields["deklar"]

    for index, rule in enumerate(field_rules):
        if not isinstance(rule, dict):
            raise ConfigError(
                f"{deklar_aggregation['_path']}: field_rules[{index}] must be an object"
            )

        target_field = rule.get("target_field")
        if not isinstance(target_field, str) or not target_field:
            raise ConfigError(
                f"{deklar_aggregation['_path']}: field_rules[{index}].target_field must be a non-empty string"
            )
        if target_field not in deklar_fields:
            raise ConfigError(
                f"{deklar_aggregation['_path']}: field_rules[{index}] target_field '{target_field}' "
                "does not exist in deklar schema"
            )

        expression = rule.get("expression")
        _validate_expression(expression, table_fields, deklar_aggregation["_path"], f"field_rules[{index}].expression")


def _validate_expression(
    expression: Any,
    table_fields: dict[str, set[str]],
    config_path: str,
    path: str,
) -> None:
    if not isinstance(expression, dict):
        raise ConfigError(f"{config_path}: {path} must be an object")

    op = expression.get("op")
    if op not in {"sum", "subtract"}:
        raise ConfigError(f"{config_path}: {path}.op must be one of: sum, subtract")

    if op == "sum":
        sources = expression.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ConfigError(f"{config_path}: {path}.sources must be a non-empty list for sum")

        for source_index, source in enumerate(sources):
            if not isinstance(source, dict):
                raise ConfigError(
                    f"{config_path}: {path}.sources[{source_index}] must be an object"
                )

            table = source.get("table")
            field = source.get("field")
            if table not in {"pokupki", "prodagbi"}:
                raise ConfigError(
                    f"{config_path}: {path}.sources[{source_index}].table must be 'pokupki' or 'prodagbi'"
                )
            if not isinstance(field, str) or not field:
                raise ConfigError(
                    f"{config_path}: {path}.sources[{source_index}].field must be a non-empty string"
                )
            if field not in table_fields[table]:
                raise ConfigError(
                    f"{config_path}: {path}.sources[{source_index}] references unknown "
                    f"field '{field}' in table '{table}'"
                )
        return

    left = expression.get("left")
    right = expression.get("right")
    if left is None or right is None:
        raise ConfigError(f"{config_path}: {path} subtract op requires both left and right expressions")
    _validate_expression(left, table_fields, config_path, f"{path}.left")
    _validate_expression(right, table_fields, config_path, f"{path}.right")


def _validate_ledger_columns(ledger_columns: dict[str, Any]) -> None:
    required: dict[str, tuple[str, ...]] = {
        "company VAT": ("company_vat",),
        "counterparty VAT": ("counterparty_vat", "partner_vat"),
        "tax_period": ("tax_period",),
        "document type": ("document_type",),
        "document number": ("document_number", "purchase_ref", "sales_move_name"),
        "document date": ("document_date", "date"),
        "balance": ("balance",),
        "tax_tag_ids": ("tax_tag_ids",),
    }

    missing: list[str] = []
    for semantic_key, acceptable_keys in required.items():
        if not any(_non_empty_string(ledger_columns.get(candidate)) for candidate in acceptable_keys):
            missing.append(f"{semantic_key} (expected one of: {', '.join(acceptable_keys)})")

    if missing:
        raise ConfigError(
            f"{ledger_columns['_path']}: missing required ledger semantic mappings: "
            + "; ".join(missing)
        )

    if not _non_empty_string(ledger_columns.get("company_vat")):
        raise ConfigError(f"{ledger_columns['_path']}: company_vat mapping must not be empty")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""
