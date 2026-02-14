from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MappingResult:
    pokupki_rows: list[dict[str, Any]]
    prodagbi_rows: list[dict[str, Any]]
    warnings: list[str]
