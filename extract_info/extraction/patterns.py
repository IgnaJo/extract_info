"""Patrones regex para extracción de campos desde texto PDF."""

from __future__ import annotations

import re
from enum import Enum


class DocumentType(str, Enum):
    CREDIT_CARD = "credit_card"
    NOTARIZED = "notarized"


# --- Credit Card Contract Patterns ---

PAT_NOMBRE_CC = re.compile(
    r"Nombre\s*(?:Completo\s*)?:",
    re.IGNORECASE,
)

PAT_NOMBRE_VARIANTS = re.compile(
    r"Nombre\s*:\s*(.+?)(?:\n|Rut|$)",
    re.IGNORECASE,
)

PAT_RUT_CC = re.compile(
    r"Rut\s*:\s*([\d.]+-[\dkK])",
    re.IGNORECASE,
)

PAT_RUT_VARIANTS = re.compile(
    r"(?:RUT|Rut)\s*:\s*([\d.]+-[\dkK])",
    re.IGNORECASE,
)

# Para bloques combinados "Nombre\nRUT" en layouts de 2 columnas
PAT_RUT_IN_NAME_BLOCK = re.compile(
    r"([\d.]+-[\dkK])$",
    re.MULTILINE,
)

PAT_FECHA_NACIMIENTO = re.compile(
    r"Fecha\s+Nacimiento:\s*(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

PAT_FECHA_VIGENTE = re.compile(
    r"(?:Vigentes\s+al\s+(\d{2}[-/]\d{2}[-/]\d{4})|(\d{2}[-/]\d{2}[-/]\d{4})\s*\n\s*Vigentes\s+al)",
    re.IGNORECASE,
)

# Fallback: "Vigentes al" followed by date on next line
PAT_FECHA_VIGENTE_FALLBACK = re.compile(
    r"Vigentes\s+al\s*[:\n]\s*(\d{2}[-/]\d{2}[-/]\d{4})",
    re.IGNORECASE,
)

# Also handle "Vigentes al :" with date on next line
PAT_FECHA_VIGENTE_NEXT_LINE = re.compile(
    r"Vigentes\s+al\s*:\s*\n\s*(\d{2}[-/]\d{2}[-/]\d{4})",
    re.IGNORECASE,
)

# Date on the line BEFORE "Vigentes al" (separated by newline)
PAT_FECHA_VIGENTE_BEFORE = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s*\n\s*.*Vigentes\s+al",
    re.IGNORECASE,
)

PAT_PROTO_VALUE = re.compile(r"(\d{5,7})")

PAT_REP_VALUE = re.compile(r"(\d{4,7})")

PAT_FECHA_REP_VALUE = re.compile(r"(\d{2}-\d{2}-\d{4})")


# --- Notarized Document Patterns ---

PAT_NOMBRE_NOT = re.compile(
    r"Nombre\s*:\s*(.+?)(?:\n|RUT|$)",
    re.IGNORECASE,
)

PAT_RUT_NOT = re.compile(
    r"RUN\s+del\s+Firmante\s*:\s*([\d.]+-[\dkK])",
    re.IGNORECASE,
)

PAT_FECHA_FIRMA = re.compile(
    r"Fecha\s+de\s+la\s+Firma\s*:\s*(\d{2}[-/]\d{2}[-/]\d{4})",
    re.IGNORECASE,
)

PAT_PROTO_LABEL = re.compile(
    r"PROTOCOLIZADO\s+N[°º]?\s*(\d+)",
    re.IGNORECASE,
)

PAT_REP_LABEL = re.compile(
    r"(?:\*\*)?REP\s+N[°º]?\s*(\d+)",
    re.IGNORECASE,
)

PAT_FECHA_REP_LABEL = re.compile(
    r"(?:\*\*)?REP\s+N[°º]?\s*\d+.*?DE\s*(\d{2}[-/]\d{2}[-/]\d{4})",
    re.IGNORECASE,
)


# --- Generic ---

PAT_FECHA_GENERAL = re.compile(r"\d{2}[-/]\d{2}[-/]\d{4}")

PAT_NOMBRE_GENERIC = re.compile(
    r"Nombre\s+(?:Completo\s*)?:\s*(.+?)(?:\n|RUT|$)",
    re.IGNORECASE,
)

PAT_RUT_GENERIC = re.compile(
    r"(?:RUT|RUN)\s*:\s*([\d.]+-[\dkK])",
    re.IGNORECASE,
)


# --- Document Type Detection ---

def detect_document_type(text: str) -> DocumentType:
    """Detecta el tipo de documento basado en contenido de la primera página."""
    has_nombre_completo = bool(re.search(r"Nombre\s+Completo:", text, re.IGNORECASE))
    has_vigente = bool(re.search(r"Vigentes\s+al", text, re.IGNORECASE))
    has_run_firmante = bool(re.search(r"RUN\s+del\s+Firmante", text, re.IGNORECASE))
    has_fecha_firma = bool(re.search(r"Fecha\s+de\s+la\s+Firma", text, re.IGNORECASE))

    if has_nombre_completo and has_vigente:
        return DocumentType.CREDIT_CARD
    if has_run_firmante or has_fecha_firma:
        return DocumentType.NOTARIZED

    return DocumentType.CREDIT_CARD


# --- Normalization ---

def normalizar_fecha(fecha_str: str) -> str:
    """Normaliza fecha a formato dd-mm-yyyy."""
    return fecha_str.replace("/", "-")


def extraer_fecha(texto: str, patron: re.Pattern) -> str | None:
    """Extrae y normaliza la primera fecha encontrada por un patrón."""
    match = patron.search(texto)
    if match:
        return normalizar_fecha(match.group(1) if match.lastindex else match.group(0))
    return None


def extraer_valor_numerico(texto: str, patron: re.Pattern) -> str | None:
    """Extrae el primer valor numérico encontrado por un patrón."""
    match = patron.search(texto)
    if match:
        return match.group(1)
    return None
