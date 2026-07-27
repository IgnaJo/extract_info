"""Extracción de texto desde PDFs usando PyMuPDF con agrupación espacial."""

from __future__ import annotations

from dataclasses import dataclass

import fitz  # PyMuPDF


@dataclass
class TextBlock:
    """Bloque de texto con posición espacial."""

    text: str
    top: float
    left: float
    bottom: float
    right: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top


@dataclass
class PageData:
    """Datos extraídos de una página del PDF."""

    page_number: int
    blocks: list[TextBlock]

    @property
    def full_text(self) -> str:
        return "\n".join(b.text for b in self.blocks)


def extract_page_text(page: fitz.Page) -> PageData:
    """Extrae texto de una página ordenado por posición espacial."""
    blocks_raw = page.get_text("blocks")
    blocks = []
    for b in blocks_raw:
        x0, y0, x1, y1, text, _block_no, _block_type = b
        text_clean = text.strip()
        if text_clean:
            blocks.append(
                TextBlock(text=text_clean, top=y0, left=x0, bottom=y1, right=x1)
            )
    blocks.sort(key=lambda b: (b.top, b.left))
    return PageData(page_number=page.number, blocks=blocks)


def extract_full_text(doc: fitz.Document) -> list[PageData]:
    """Extrae texto de todas las páginas del documento."""
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pages.append(extract_page_text(page))
    return pages


def get_page_count(doc: fitz.Document) -> int:
    """Retorna el total de páginas del documento."""
    return len(doc)


def open_pdf(path: str) -> fitz.Document:
    """Abre un archivo PDF. El caller debe cerrar el documento."""
    return fitz.open(path)
