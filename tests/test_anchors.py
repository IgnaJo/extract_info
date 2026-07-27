"""Tests para anchor-based search."""

import re

import pytest

from extract_info.extraction.anchors import (
    extract_value_after_anchor,
    find_anchor,
    search_in_pages,
)
from extract_info.extraction.text_reader import PageData, TextBlock


def _make_blocks(texts: list[str], start_top: float = 0) -> list[TextBlock]:
    """Crea bloques de texto de prueba."""
    blocks = []
    for i, text in enumerate(texts):
        top = start_top + i * 20.0
        blocks.append(TextBlock(text=text, top=top, left=72.0, bottom=top + 15.0, right=500.0))
    return blocks


PAT_NOMBRE = re.compile(r"Nombre completo\s*:\s*(.*)", re.IGNORECASE)
PAT_RUT = re.compile(r"RUT\s*:\s*(\d{1,2}\.\d{3}\.\d{3}-[\dkK])", re.IGNORECASE)


class TestFindAnchor:
    def test_finds_anchor(self):
        blocks = _make_blocks(["Some text", "Nombre completo: Juan Pérez", "More text"])
        result = find_anchor(blocks, PAT_NOMBRE)
        assert result is not None
        block, match = result
        assert "Juan Pérez" in block.text

    def test_returns_none_when_not_found(self):
        blocks = _make_blocks(["Some text", "No anchor here"])
        assert find_anchor(blocks, PAT_NOMBRE) is None


class TestExtractValueAfterAnchor:
    def test_extracts_from_same_match(self):
        blocks = _make_blocks(["Nombre completo: María López"])
        value = extract_value_after_anchor(blocks, PAT_NOMBRE)
        assert value == "María López"

    def test_extracts_rut(self):
        blocks = _make_blocks(["RUT: 12.345.678-5"])
        value = extract_value_after_anchor(blocks, PAT_RUT)
        assert value == "12.345.678-5"

    def test_returns_none_when_no_anchor(self):
        blocks = _make_blocks(["Nothing here"])
        assert extract_value_after_anchor(blocks, PAT_NOMBRE) is None

    def test_fallback_to_next_block(self):
        blocks = _make_blocks(["Nombre completo:", "Juan Pérez González"])
        value = extract_value_after_anchor(blocks, PAT_NOMBRE)
        assert value == "Juan Pérez González"


class TestSearchInPages:
    def test_searches_multiple_pages(self):
        page0 = PageData(
            page_number=0,
            blocks=_make_blocks(["Other content"]),
        )
        page1 = PageData(
            page_number=1,
            blocks=_make_blocks(["Nombre completo: Carlos Soto"]),
        )
        result = search_in_pages([page0, page1], PAT_NOMBRE)
        assert result is not None
        value, page_num = result
        assert value == "Carlos Soto"
        assert page_num == 1

    def test_respects_page_indices(self):
        page0 = PageData(
            page_number=0,
            blocks=_make_blocks(["Nombre completo: Should not find"]),
        )
        page1 = PageData(
            page_number=1,
            blocks=_make_blocks(["Nombre completo: Should find"]),
        )
        result = search_in_pages([page0, page1], PAT_NOMBRE, page_indices=[1])
        assert result is not None
        assert result[1] == 1

    def test_returns_none_when_not_found(self):
        page0 = PageData(page_number=0, blocks=_make_blocks(["No match"]))
        assert search_in_pages([page0], PAT_NOMBRE) is None
