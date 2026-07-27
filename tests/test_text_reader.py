"""Tests para text_reader (extracción PyMuPDF)."""

import os
import tempfile

import fitz
import pytest

from extract_info.extraction.text_reader import (
    PageData,
    TextBlock,
    extract_full_text,
    extract_page_text,
    get_page_count,
    open_pdf,
)


def _create_test_pdf(text_per_page: list[str], path: str) -> None:
    """Crea un PDF de prueba con texto dado por página."""
    doc = fitz.open()
    for text in text_per_page:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


@pytest.fixture
def test_pdf(tmp_path):
    """Fixture: crea un PDF temporal de 3 páginas."""
    path = str(tmp_path / "test.pdf")
    pages = [
        "PROTOCOLIZADO N° 12345\nREP N° 6789 DE 25-06-2024",
        "Contenido del contrato aquí.\nPágina 2.",
        "Nombre completo: Juan Pérez González\nRUT: 12.345.678-5\nFecha: 25-06-2024",
    ]
    _create_test_pdf(pages, path)
    return path


class TestOpenPdf:
    def test_opens_valid_pdf(self, test_pdf):
        doc = open_pdf(test_pdf)
        assert len(doc) == 3
        doc.close()

    def test_raises_on_missing(self):
        with pytest.raises(Exception):
            open_pdf("/nonexistent/file.pdf")


class TestGetPageCount:
    def test_count(self, test_pdf):
        doc = open_pdf(test_pdf)
        assert get_page_count(doc) == 3
        doc.close()


class TestExtractPageText:
    def test_extracts_blocks(self, test_pdf):
        doc = open_pdf(test_pdf)
        page_data = extract_page_text(doc[0])
        assert isinstance(page_data, PageData)
        assert page_data.page_number == 0
        assert len(page_data.blocks) > 0
        doc.close()

    def test_blocks_have_text(self, test_pdf):
        doc = open_pdf(test_pdf)
        page_data = extract_page_text(doc[0])
        all_text = page_data.full_text
        assert "PROTOCOLIZADO" in all_text
        doc.close()


class TestExtractFullText:
    def test_extracts_all_pages(self, test_pdf):
        doc = open_pdf(test_pdf)
        pages = extract_full_text(doc)
        assert len(pages) == 3
        doc.close()

    def test_page_order(self, test_pdf):
        doc = open_pdf(test_pdf)
        pages = extract_full_text(doc)
        assert pages[0].page_number == 0
        assert pages[1].page_number == 1
        assert pages[2].page_number == 2
        doc.close()

    def test_full_text_concatenation(self, test_pdf):
        doc = open_pdf(test_pdf)
        pages = extract_full_text(doc)
        last_page_text = pages[-1].full_text
        assert "Juan Pérez" in last_page_text
        doc.close()


class TestTextBlock:
    def test_properties(self):
        block = TextBlock(text="test", top=10.0, left=20.0, bottom=30.0, right=50.0)
        assert block.width == 30.0
        assert block.height == 20.0
