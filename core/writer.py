from __future__ import annotations

import csv
import re
from decimal import Decimal
from pathlib import Path
from typing import Any


CSV_ENCODING = "utf-8"
CSV_DELIMITER = ","
CSV_NEWLINE = "\r\n"
ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def write_csv_tables(
    pokupki_rows: list[dict[str, Any]],
    prodagbi_rows: list[dict[str, Any]],
    schemas: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, str]:
    """Write VAT table CSV files based on schema-defined column order."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pokupki_schema = schemas.get("pokupki")
    prodagbi_schema = schemas.get("prodagbi")

    if not isinstance(pokupki_schema, dict):
        raise ValueError("Missing or invalid 'pokupki_schema' in schemas")
    if not isinstance(prodagbi_schema, dict):
        raise ValueError("Missing or invalid 'prodagbi_schema' in schemas")

    pokupki_columns = _schema_field_names(pokupki_schema)
    prodagbi_columns = _schema_field_names(prodagbi_schema)

    pokupki_file = output_path / "pokupki.csv"
    prodagbi_file = output_path / "prodagbi.csv"

    for i, row in enumerate(pokupki_rows, start=1):
        row["journal_row_number"] = i

    for i, row in enumerate(prodagbi_rows, start=1):
        row["journal_row_number"] = i


    _write_csv(pokupki_file, pokupki_rows, pokupki_columns)
    _write_csv(prodagbi_file, prodagbi_rows, prodagbi_columns)

    return {
        "pokupki_csv": str(pokupki_file),
        "prodagbi_csv": str(prodagbi_file),
    }


def write_txt_tables(
    pokupki_rows: list[dict[str, Any]],
    prodagbi_rows: list[dict[str, Any]],
    schemas: dict[str, Any],
    output_dir: str | Path,
) -> tuple[dict[str, str], list[str]]:
    """Write VAT table TXT files based on schema-defined fixed-width metadata."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pokupki_schema = schemas.get("pokupki")
    prodagbi_schema = schemas.get("prodagbi")

    if not isinstance(pokupki_schema, dict):
        raise ValueError("Missing or invalid 'pokupki_schema' in schemas")
    if not isinstance(prodagbi_schema, dict):
        raise ValueError("Missing or invalid 'prodagbi_schema' in schemas")

    warnings: list[str] = []
    pokupki_file = output_path / "pokupki.txt"
    prodagbi_file = output_path / "prodagbi.txt"

    _write_txt_table(pokupki_file, pokupki_rows, pokupki_schema, "pokupki", warnings)
    _write_txt_table(prodagbi_file, prodagbi_rows, prodagbi_schema, "prodagbi", warnings)

    return {
        "pokupki_txt": str(pokupki_file),
        "prodagbi_txt": str(prodagbi_file),
    }, warnings


def write_deklar_csv(
    deklar_row: dict[str, Any],
    schemas: dict[str, Any],
    output_dir: str | Path,
) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    deklar_schema = schemas.get("deklar")
    if not isinstance(deklar_schema, dict):
        raise ValueError("Missing or invalid 'deklar' schema in schemas")

    deklar_columns = _schema_field_names(deklar_schema)
    deklar_file = output_path / "deklar.csv"
    _write_csv(deklar_file, [deklar_row], deklar_columns)
    return str(deklar_file)


def write_deklar_txt(
    deklar_row: dict[str, Any],
    schemas: dict[str, Any],
    output_dir: str | Path,
) -> tuple[str, list[str]]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    deklar_schema = schemas.get("deklar")
    if not isinstance(deklar_schema, dict):
        raise ValueError("Missing or invalid 'deklar' schema in schemas")

    warnings: list[str] = []
    deklar_file = output_path / "deklar.txt"
    _write_txt_table(deklar_file, [deklar_row], deklar_schema, "deklar", warnings)
    return str(deklar_file), warnings


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


def _write_txt_table(
    file_path: Path,
    rows: list[dict[str, Any]],
    schema: dict[str, Any],
    table_name: str,
    warnings: list[str],
) -> None:
    fields = schema.get("fields")
    line_length = schema.get("line_length")
    file_encoding = schema.get("file_encoding") or "cp1251"
    newline = _schema_newline(schema.get("newline"))

    if not isinstance(fields, list):
        raise ValueError(f"Schema '{table_name}' fields must be a list")
    if not isinstance(line_length, int) or line_length <= 0:
        raise ValueError(f"Schema '{table_name}' line_length must be a positive integer")

    with file_path.open("w", encoding=file_encoding, newline="") as txt_file:
        for row_index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise ValueError(f"Row is not a dict: {row!r}")

            row_for_write = dict(row)
            row_for_write["journal_row_number"] = row_index
            line = _build_txt_line(row_for_write, fields, line_length, table_name, row_index, warnings)
            txt_file.write(line)
            txt_file.write(newline)


def _build_txt_line(
    row: dict[str, Any],
    fields: list[Any],
    line_length: int,
    table_name: str,
    row_index: int,
    warnings: list[str],
) -> str:
    buffer = [" "] * line_length

    for field in fields:
        if not isinstance(field, dict):
            continue

        internal_name = field.get("internal_name")
        start_pos = field.get("start_pos")
        length = field.get("length")
        if not isinstance(internal_name, str) or not isinstance(start_pos, int) or not isinstance(length, int):
            continue

        if start_pos < 1 or length < 0:
            raise ValueError(
                f"Invalid field positioning for {table_name}.{internal_name}: start_pos={start_pos}, length={length}"
            )

        raw_value = row.get(internal_name)
        if internal_name == "document_date":
            raw_value = _format_txt_document_date(raw_value)

        value = _to_txt_string(raw_value, field)

        if len(value) > length:
            warnings.append(
                f"{table_name}[{row_index}].{internal_name}: value length {len(value)} exceeds field length {length}; truncated"
            )
            value = value[:length]

        align = str(field.get("align") or "left").lower()
        pad_char = str(field.get("pad_char") or " ")
        if not pad_char:
            pad_char = " "
        pad_char = pad_char[0]
        padded_value = value.rjust(length, pad_char) if align == "right" else value.ljust(length, pad_char)

        start_index = start_pos - 1
        end_index = start_index + length
        if end_index > line_length:
            raise ValueError(
                f"Field {table_name}.{internal_name} overflows line_length {line_length}: {start_pos}+{length}-1"
            )

        buffer[start_index:end_index] = list(padded_value)

    line = "".join(buffer)
    if len(line) != line_length:
        raise ValueError(f"Line length mismatch for {table_name}[{row_index}]: {len(line)} != {line_length}")
    return line


def _to_txt_string(value: Any, field: dict[str, Any]) -> str:
    if value is None:
        return ""

    field_type = str(field.get("type") or "").lower()
    decimals = field.get("decimals")

    if field_type in {"float64", "decimal", "number", "numeric"} or isinstance(value, Decimal):
        decimal_value = Decimal(str(value))
        if isinstance(decimals, int):
            quantizer = Decimal(1).scaleb(-decimals)
            decimal_value = decimal_value.quantize(quantizer)
            return format(decimal_value, f".{decimals}f")
        return format(decimal_value, "f")

    return str(value)


def _format_txt_document_date(value: Any) -> Any:
    # Format date for TXT: dd/mm/yyyy
    if isinstance(value, str) and ISO_DATE_PATTERN.fullmatch(value):
        year, month, day = value.split("-")
        return f"{day}/{month}/{year}"
    return value


def _schema_newline(value: Any) -> str:
    normalized = str(value or "CRLF").upper()
    if normalized == "CRLF":
        return "\r\n"
    if normalized == "LF":
        return "\n"
    if normalized == "CR":
        return "\r"
    return str(value)
