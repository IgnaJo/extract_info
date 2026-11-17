"""Esquema declarativo de columnas compartido por extracción, CSV y GUI.

La fuente de verdad es ``NODE_SPECS[nodo]["columns"]``; ``csv_columns`` es una
lista derivada de ``key`` para mantener compatibilidad con CSV y tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ColumnKind(str, Enum):
    """Semántica de una columna, independiente del pipeline que la produce."""

    TEXT = "text"
    DATE = "date"
    NUMBER = "number"
    FILENAME = "filename"
    FOLDER = "folder"
    STATUS = "status"
    NOTES = "notes"


@dataclass(frozen=True)
class ColumnSpec:
    """Definición declarativa de una columna de salida."""

    key: str
    label: str
    kind: ColumnKind = ColumnKind.TEXT


def column_keys(columns: Iterable[ColumnSpec]) -> list[str]:
    """Claves en orden de declaración (esquema del CSV)."""

    return [column.key for column in columns]


def find_kind(columns: Iterable[ColumnSpec], kind: ColumnKind) -> ColumnSpec | None:
    """Primera columna de un tipo dado, o ``None``."""

    return next((column for column in columns if column.kind == kind), None)
