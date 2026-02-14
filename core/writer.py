from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any


CSV_ENCODING = "utf-8"
CSV_DELIMITER = ","
CSV_NEWLINE = "\r\n"


def write_csv_tables(
    pokupki_rows: list[dict[str, Any]],
    prodagbi_rows: list[dict[str, Any]],
    schemas: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, str]:
    """Write VAT table CSV files based on schema-defined column order.

    TXT generation is intentionally not implemented in this version.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pokupki_schema = schemas.get("pokupki_schema")
    prodagbi_schema = schemas.get("prodagbi_schema")

    if not isinstance(pokupki_schema, dict):
        raise ValueError("Missing or invalid 'pokupki_schema' in schemas")
    if not isinstance(prodagbi_schema, dict):
        raise ValueError("Missing or invalid 'prodagbi_schema' in schemas")

    pokupki_columns = _schema_field_names(pokupki_schema)
    prodagbi_columns = _schema_field_names(prodagbi_schema)

    pokupki_file = output_path / "pokupki.csv"
    prodagbi_file = output_path / "prodagbi.csv"

    _write_csv(pokupki_file, pokupki_rows, pokupki_columns)
    _write_csv(prodagbi_file, prodagbi_rows, prodagbi_columns)

    # Placeholder for upcoming TXT writer support.
    _ = _txt_config_placeholders(pokupki_schema, prodagbi_schema)

    return {
        "pokupki_csv": str(pokupki_file),
        "prodagbi_csv": str(prodagbi_file),
    }


def _schema_field_names(schema: dict[str, Any]) -> list[str]:
    fields = schema.get("fields", [])
    if not isinstance(fields, list):
        raise ValueError("Schema 'fields' must be a list")

    names: list[str] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        internal_name = field.get("internal_name")
        if isinstance(internal_name, str) and internal_name:
            names.append(internal_name)

    if not names:
        raise ValueError("Schema does not contain any valid field internal_name values")

    return names


def _write_csv(file_path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with file_path.open("w", encoding=CSV_ENCODING, newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=columns,
            delimiter=CSV_DELIMITER,
            lineterminator=CSV_NEWLINE,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"Row is not a dict: {row!r}")

            normalized_row = {column: _to_csv_value(row.get(column)) for column in columns}
            writer.writerow(normalized_row)


def _to_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _txt_config_placeholders(
    pokupki_schema: dict[str, Any],
    prodagbi_schema: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Collect TXT-related schema metadata for future writer implementation."""
    return {
        "pokupki": {
            "file_encoding": pokupki_schema.get("file_encoding"),
            "newline": pokupki_schema.get("newline"),
            "line_length": pokupki_schema.get("line_length"),
        },
        "prodagbi": {
            "file_encoding": prodagbi_schema.get("file_encoding"),
            "newline": prodagbi_schema.get("newline"),
            "line_length": prodagbi_schema.get("line_length"),
        },
    }
