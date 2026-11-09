"""Tests para el CLI unificado con selección de pipeline."""

from __future__ import annotations

import csv
import subprocess
import sys

import fitz
import pytest

from extract_info.batch import (
    PipelineFolderResult,
    list_pipelines,
    process_batch_pipeline,
    process_folder_pipeline,
)
from extract_info.csv_writer import write_pipeline_csvs
from extract_info.pipelines.base import NODE_SPECS, NodeResult


def _create_pdf(text: str, path: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


@pytest.fixture
def retail_tree(tmp_path):
    """Carpeta con dos PDFs de contrato retail."""
    folder = tmp_path / "carpeta_retail"
    folder.mkdir()
    _create_pdf(
        "PROTOCOLIZADO N° 11111\nREP N° 2222 DE 01-01-2024\n"
        "Nombre completo: Ana\nRUT: 11.111.111-1\nVigentes al 01-01-2024",
        str(folder / "doc1.pdf"),
    )
    _create_pdf(
        "PROTOCOLIZADO N° 33333\nREP N° 4444 DE 02-02-2024\n"
        "Nombre completo: Beto\nRUT: 22.222.222-2\nVigentes al 02-02-2024",
        str(folder / "doc2.pdf"),
    )
    return tmp_path


def test_list_pipelines():
    assert list_pipelines() == ["aseguradora", "retail"]


def test_unknown_pipeline_fails_fast(tmp_path):
    with pytest.raises(ValueError) as exc:
        process_batch_pipeline(str(tmp_path), pipeline="inexistente")
    message = str(exc.value)
    assert "inexistente" in message
    assert "aseguradora" in message and "retail" in message


def test_retail_pipeline_keeps_columns_and_row(retail_tree):
    folder = str(retail_tree / "carpeta_retail")
    result = process_folder_pipeline(folder, pipeline="retail")

    assert isinstance(result, PipelineFolderResult)
    assert result.nombre_carpeta == "carpeta_retail"
    assert result.columns == NODE_SPECS["Retail"]["csv_columns"]
    assert len(result.rows) == 2
    assert {row["nombre_archivo"] for row in result.rows} == {"doc1.pdf", "doc2.pdf"}
    assert {row["rut"] for row in result.rows} == {"11.111.111-1", "22.222.222-2"}


def test_aseguradora_pipeline_is_dispatched(tmp_path, monkeypatch):
    """El despacho usa el nodo Aseguradora y sus columnas, sin tocar Retail."""
    from extract_info import batch

    fake_rows = [{"Archivo": "x.pdf", "Estado": "OK"}]
    calls = []

    def fake_runner(folder_path):
        calls.append(folder_path)
        return NodeResult(
            rows=fake_rows,
            columns=NODE_SPECS["Aseguradora"]["csv_columns"],
            logs=[],
            total_processed=1,
            success_count=1,
        )

    monkeypatch.setitem(batch._PIPELINE_RUNNERS, "aseguradora", fake_runner)

    result = process_folder_pipeline(str(tmp_path), pipeline="aseguradora")

    assert calls == [str(tmp_path)]
    assert result.rows == fake_rows
    assert result.columns == NODE_SPECS["Aseguradora"]["csv_columns"]


def test_batch_pipeline_sorts_folders(retail_tree):
    results = process_batch_pipeline(str(retail_tree), pipeline="retail", max_workers=1)

    assert [r.nombre_carpeta for r in results] == ["carpeta_retail"]


def test_write_pipeline_csvs_one_file_per_folder(tmp_path):
    results = [
        PipelineFolderResult("a", [{"Archivo": "1.pdf", "Estado": "OK"}], ["Archivo", "Estado"]),
        PipelineFolderResult("b", [{"Archivo": "2.pdf", "Estado": "OK"}], ["Archivo", "Estado"]),
    ]

    paths = write_pipeline_csvs(results, str(tmp_path / "out"))

    assert [p.rsplit("/", 1)[-1] for p in paths] == ["resultado_a.csv", "resultado_b.csv"]
    with open(paths[0], encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"Archivo": "1.pdf", "Estado": "OK"}]


def test_write_pipeline_csvs_unified(tmp_path):
    results = [
        PipelineFolderResult("a", [{"Archivo": "1.pdf"}], ["Archivo"]),
        PipelineFolderResult("b", [{"Archivo": "2.pdf"}], ["Archivo"]),
    ]

    paths = write_pipeline_csvs(results, str(tmp_path / "out"), unified=True)

    assert len(paths) == 1
    assert paths[0].endswith("resultado_unificado.csv")
    with open(paths[0], encoding="utf-8-sig", newline="") as handle:
        assert [row["Archivo"] for row in csv.DictReader(handle)] == ["1.pdf", "2.pdf"]


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "extract_info", *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_cli_help_runs():
    proc = _run_cli("--help")

    assert proc.returncode == 0, proc.stderr
    assert "--pipeline" in proc.stdout
    assert "aseguradora" in proc.stdout


def test_cli_default_pipeline_is_retail(retail_tree, tmp_path):
    out = tmp_path / "out"

    proc = _run_cli("-i", str(retail_tree), "-o", str(out), "-w", "1")

    assert proc.returncode == 0, proc.stderr
    csv_path = out / "resultado_carpeta_retail.csv"
    assert csv_path.exists()
    with open(csv_path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert list(rows[0]) == NODE_SPECS["Retail"]["csv_columns"]


def test_cli_accepts_aseguradora_and_unified(retail_tree, tmp_path):
    out = tmp_path / "out"

    proc = _run_cli(
        "-i", str(retail_tree), "-o", str(out), "-p", "aseguradora", "--unified", "-w", "1"
    )

    assert proc.returncode == 0, proc.stderr
    unified = out / "resultado_unificado.csv"
    assert unified.exists()
    with open(unified, encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == NODE_SPECS["Aseguradora"]["csv_columns"]
