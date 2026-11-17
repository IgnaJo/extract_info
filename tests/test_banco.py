"""Tests del pipeline Banco contra el documento de ejemplo."""

from __future__ import annotations

import os

import fitz
import pytest

from extract_info.pipelines.banco import banco_process_single
from extract_info.pipelines.base import NODE_SPECS

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
EXAMPLE_PDF = os.path.join(ASSETS_DIR, "EXAMPLE_BANCO.pdf")

EXPECTED_COLUMNS = [
    "numero operacion",
    "fecha firma",
    "rut",
    "nombre",
    "nº repertorio",
    "Nº proto",
    "fecha repertorio",
    "número de paginas documento",
    "Archivo",
    "Estado",
]

pytestmark = pytest.mark.skipif(
    not os.path.exists(EXAMPLE_PDF),
    reason="Falta assets/EXAMPLE_BANCO.pdf (no se versiona)",
)


def test_banco_schema_order():
    assert NODE_SPECS["Banco"]["csv_columns"] == EXPECTED_COLUMNS


def test_banco_extracts_page_9_fields():
    row = banco_process_single(EXAMPLE_PDF)

    assert row["numero operacion"] == "1234567890"
    assert row["fecha firma"] == "12-04-2026"
    assert row["rut"] == "11111111-1"
    assert row["nombre"] == "NAME1 NAME2 LASTNAME1 LASTNAME2"


def test_banco_extracts_page_1_repertorio():
    row = banco_process_single(EXAMPLE_PDF)

    assert row["nº repertorio"] == "90985"
    assert row["Nº proto"] == "171516"
    assert row["fecha repertorio"] == "09-11-2026"


def test_banco_counts_total_pdf_pages():
    row = banco_process_single(EXAMPLE_PDF)

    assert row["número de paginas documento"] == 14
    assert row["Estado"] == "OK"


def test_banco_short_document_reports_error(tmp_path):
    path = tmp_path / "corto.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(str(path))
    doc.close()

    row = banco_process_single(str(path))

    assert row["Estado"].startswith("ERROR")
    assert row["número de paginas documento"] == 2
    assert row["numero operacion"] is None
