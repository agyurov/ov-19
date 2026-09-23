from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.text_encoding import make_encodable


CSV_ENCODING = "utf-8"
CSV_DELIMITER = ","
CSV_NEWLINE = "\r\n"
SECTION_ORDER = ("VHR", "VDR", "VTR", "TTR", "VIR", "CHR")


def build_vies_data(
    prodagbi_rows: list[dict],
    reporting_period: str,
    declarer_id: str,
    declarer_name: str,
    registered_vat: str,
    registered_name: str,
    registered_address: str,
) -> dict[str, Any]:
    groups: defaultdict[str, Decimal] = defaultdict(Decimal)

    for row in prodagbi_rows:
        if not isinstance(row, dict):
            continue

        vat = (row.get("counterparty_vat") or "").strip()
        amount = _to_decimal(row.get("base_services_21_2", Decimal("0")))

        if vat and vat != "9999999999999" and amount != Decimal("0"):
            groups[vat] += amount

    normalized_period = _normalize_reporting_period(reporting_period, prodagbi_rows)

    vir_rows: list[dict[str, Any]] = []
    total_tax_base = Decimal("0")

    for line_number, vat in enumerate(sorted(groups.keys()), start=1):
        services_tax_base = groups[vat]
        total_tax_base += services_tax_base

        vir_rows.append(
            {
                "vir_section_code": "VIR",
                "line_number": Decimal(line_number),
                "counterparty_vat": vat,
                "services_tax_base": services_tax_base,
                "goods_tax_base": Decimal("0"),
                "triangular_tax_base": Decimal("0"),
                "vir_reporting_period": "",
            }
        )

    return {
        "VHR": {
            "vhr_section_code": "VHR",
            "reporting_period": normalized_period,
            "total_record_count": Decimal(len(vir_rows)),
        },
        "VDR": {
            "vdr_section_code": "VDR",
            "declarer_id": declarer_id,
            "declarer_name": declarer_name,
            "declarer_city": "",
            "declarer_postal_code": "",
            "declarer_address": "",
            "declarer_person_type": "",
        },
        "VTR": {
            "vtr_section_code": "VTR",
            "registered_vat_number": registered_vat,
            "registered_name": registered_name,
            "registered_address": registered_address,
        },
        "TTR": {
            "ttr_section_code": "TTR",
            "total_tax_base": total_tax_base,
            "vod_tax_base": Decimal("0"),
        },
        "VIR": vir_rows,
        "CHR": {
            "chr_section_code": "CHR",
            # The NAP-accepted file has 0 here even with VIR lines; meaning not confirmed yet.
            "chr_record_count": Decimal("0"),
        },
    }


def write_vies_csv(vies_data: dict[str, Any], output_dir: str | Path) -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    vies_file = output_path / "vies.csv"
    columns = [
        "line_number",
        "counterparty_vat",
        "services_tax_base",
        "goods_tax_base",
        "triangular_tax_base",
    ]

    vir_rows = vies_data.get("VIR")
    if not isinstance(vir_rows, list):
        raise ValueError("vies_data['VIR'] must be a list")

    with vies_file.open("w", encoding=CSV_ENCODING, newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=columns,
            delimiter=CSV_DELIMITER,
            lineterminator=CSV_NEWLINE,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in vir_rows:
            if not isinstance(row, dict):
                raise ValueError(f"VIR row is not a dict: {row!r}")
            writer.writerow({col: _to_csv_value(row.get(col)) for col in columns})

    return str(vies_file)


def write_vies_txt(
    vies_data: dict[str, Any], vies_schema: dict[str, Any], output_dir: str | Path
) -> tuple[str, list[str]]:
    """Write vies.txt the way NAP accepts it.

    Each record type has its own width (VHR 15, VDR 373, VTR 368, TTR 27, VIR 66,
    CHR 8), records are separated by CRLF and the last line has no line ending.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_encoding = vies_schema.get("file_encoding") or "cp1251"
    newline = _schema_newline(vies_schema.get("newline"))
    fields = vies_schema.get("fields")
    if not isinstance(fields, list):
        raise ValueError("VIES schema fields must be a list")

    section_fields = _group_fields_by_section(fields)
    warnings: list[str] = []
    lines: list[str] = []

    for section_name in SECTION_ORDER:
        section_data = vies_data.get(section_name)
        rows = section_data if section_name == "VIR" else [section_data]
        if not isinstance(rows, list):
            raise ValueError(f"vies_data['{section_name}'] must be a list")

        for row_number, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise ValueError(f"vies_data['{section_name}'] row is not a dict: {row!r}")
            location = f"vies.{section_name}" + (f"[{row_number}]" if section_name == "VIR" else "")
            lines.append(
                _build_txt_line(row, section_fields[section_name], file_encoding, location, warnings)
            )

    output_file = output_path / "vies.txt"
    output_file.write_bytes(newline.join(lines).encode(file_encoding))
    return str(output_file), warnings


def _group_fields_by_section(fields: list[Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {section: [] for section in SECTION_ORDER}

    for field in fields:
        if not isinstance(field, dict):
            continue
        code = field.get("code")
        if not isinstance(code, str) or "-" not in code:
            continue
        section = code.split("-", 1)[0]
        if section in grouped:
            grouped[section].append(field)

    for section_name, section_fields in grouped.items():
        if not section_fields:
            raise ValueError(f"No fields found for VIES section {section_name}")

    return grouped


def _record_width(fields: list[dict[str, Any]]) -> int:
    return max(field["start_pos"] - 1 + field["length"] for field in fields)


def _build_txt_line(
    row: dict[str, Any],
    fields: list[dict[str, Any]],
    file_encoding: str,
    location: str,
    warnings: list[str],
) -> str:
    width = _record_width(fields)
    buffer = [" "] * width

    for field in fields:
        internal_name = field.get("internal_name")
        start_pos = field.get("start_pos")
        length = field.get("length")
        if not isinstance(internal_name, str) or not isinstance(start_pos, int) or not isinstance(length, int):
            continue

        value = _to_txt_string(row.get(internal_name), field)
        converted, used_fallback = make_encodable(value, file_encoding)
        if converted != value:
            note = " (characters without a replacement written as ?)" if used_fallback else ""
            warnings.append(f"{location}.{internal_name}: '{value}' -> '{converted}'{note}")
            value = converted

        # Transliterate before truncating so the field keeps its fixed width.
        if len(value) > length:
            warnings.append(
                f"{location}.{internal_name}: value length {len(value)} exceeds field length {length}; truncated"
            )
            value = value[:length]

        align = str(field.get("align") or "left").lower()
        pad_char = str(field.get("pad_char") or " ")[:1] or " "
        padded = value.rjust(length, pad_char) if align == "right" else value.ljust(length, pad_char)

        start_index = start_pos - 1
        buffer[start_index : start_index + length] = list(padded)

    line = "".join(buffer)
    if len(line) != width:
        raise ValueError(f"{location}: line length {len(line)} != record width {width}")
    return line


def _to_txt_string(value: Any, field: dict[str, Any]) -> str:
    if value is None:
        return ""

    field_type = str(field.get("type") or "").lower()
    decimals = field.get("decimals")

    if field_type in {"float64", "decimal", "number", "numeric"} or isinstance(value, Decimal):
        decimal_value = _to_decimal(value)
        if isinstance(decimals, int):
            quantizer = Decimal(1).scaleb(-decimals)
            decimal_value = decimal_value.quantize(quantizer)
            return format(decimal_value, f".{decimals}f")
        return format(decimal_value, "f")

    return str(value)


def _to_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _schema_newline(value: Any) -> str:
    normalized = str(value or "CRLF").upper()
    if normalized == "CRLF":
        return "\r\n"
    if normalized == "LF":
        return "\n"
    if normalized == "CR":
        return "\r"
    return str(value)


def _normalize_reporting_period(reporting_period: str, prodagbi_rows: list[dict]) -> str:
    candidate = (reporting_period or "").strip()

    if _is_yyyymm(candidate):
        return f"{candidate[4:6]}/{candidate[0:4]}"
    if _is_mm_yyyy(candidate):
        return candidate

    if prodagbi_rows and isinstance(prodagbi_rows[0], dict):
        tax_period = str(prodagbi_rows[0].get("tax_period") or "").strip()
        if _is_yyyymm(tax_period):
            return f"{tax_period[4:6]}/{tax_period[0:4]}"

    return ""


def _is_yyyymm(value: str) -> bool:
    return len(value) == 6 and value.isdigit()


def _is_mm_yyyy(value: str) -> bool:
    if len(value) != 7 or value[2] != "/":
        return False
    month = value[:2]
    year = value[3:]
    return month.isdigit() and year.isdigit()
