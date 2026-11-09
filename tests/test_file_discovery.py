"""Pruebas para el descubrimiento recursivo de PDFs."""

import os

from extract_info.extraction.file_discovery import discover_pdf_files


def test_discovers_root_and_nested_pdfs(tmp_path):
    root_pdf = tmp_path / "raiz.PDF"
    nested_dir = tmp_path / "nivel_1" / "nivel_2"
    nested_dir.mkdir(parents=True)
    nested_pdf = nested_dir / "documento.pdf"
    root_pdf.write_bytes(b"pdf")
    nested_pdf.write_bytes(b"pdf")

    files = discover_pdf_files(str(tmp_path))

    assert [item.relative_path for item in files] == [
        "nivel_1/nivel_2/documento.pdf",
        "raiz.PDF",
    ]
    assert all(os.path.isfile(item.path) for item in files)


def test_deduplicates_pdf_reached_through_symlink(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_pdf = source_dir / "documento.pdf"
    source_pdf.write_bytes(b"pdf")
    os.symlink(source_dir, tmp_path / "linked")

    files = discover_pdf_files(str(tmp_path))

    assert len(files) == 1
    assert files[0].relative_path in {
        "source/documento.pdf",
        "linked/documento.pdf",
    }
