"""Tests para el sistema de pipelines (versión simplificada)."""

import pytest

from extract_info.pipelines.base import LogEntry, NodeResult, NODE_SPECS, list_nodes, get_node_spec, process_folder
from extract_info.pipelines.retail import retail_process_folder
from extract_info.pipelines.aseguradora import aseguradora_process_folder


class TestNodeResult:
    """Tests para la clase NodeResult."""

    def test_node_result_creation(self):
        """NodeResult se crea correctamente."""
        result = NodeResult(
            rows=[{"col1": "val1"}],
            columns=["col1"],
            logs=[],
            total_processed=1,
            success_count=1,
            warning_count=0,
            error_count=0,
        )
        assert result.rows == [{"col1": "val1"}]
        assert result.columns == ["col1"]
        assert result.total_processed == 1

    def test_node_result_defaults(self):
        """NodeResult tiene valores por defecto."""
        result = NodeResult(rows=[], columns=[], logs=[])
        assert result.total_processed == 0
        assert result.success_count == 0


class TestLogEntry:
    """Tests para la clase LogEntry."""

    def test_log_entry_creation(self):
        """LogEntry se crea correctamente."""
        entry = LogEntry(
            timestamp="2024-01-01T12:00:00",
            level="INFO",
            message="Test message",
        )
        assert entry.timestamp == "2024-01-01T12:00:00"
        assert entry.level == "INFO"
        assert entry.message == "Test message"
        assert entry.filename is None


class TestPipelineSpecs:
    """Tests para las especificaciones de pipelines."""

    def test_list_nodes(self):
        """list_nodes retorna los nodos esperados."""
        nodes = list_nodes()
        assert "Retail" in nodes
        assert "Aseguradora" in nodes

    def test_get_node_spec(self):
        """get_node_spec retorna la spec correcta."""
        retail_spec = get_node_spec("Retail")
        assert retail_spec is not None
        assert retail_spec["name"] == "Retail"
        assert "csv_columns" in retail_spec

        aseguradora_spec = get_node_spec("Aseguradora")
        assert aseguradora_spec is not None
        assert aseguradora_spec["name"] == "Aseguradora"

    def test_nonexistent_node(self):
        """get_node_spec retorna None para nodo inexistente."""
        spec = get_node_spec("NonExistent")
        assert spec is None


class TestRetailPipeline:
    """Tests para el pipeline Retail."""

    def test_csv_columns(self):
        """Retail tiene las columnas esperadas."""
        spec = get_node_spec("Retail")
        expected = [
            "nombre_archivo",
            "nombre_completo",
            "rut",
            "fecha_contrato",
            "proto",
            "repertorio",
            "fecha_repertorio",
            "cantidad_hojas",
            "nombre_carpeta",
            "estado_extraccion",
            "observaciones",
        ]
        for col in expected:
            assert col in spec["csv_columns"]


class TestAseguradoraPipeline:
    """Tests para el pipeline Aseguradora."""

    def test_csv_columns(self):
        """Aseguradora tiene las columnas esperadas."""
        spec = get_node_spec("Aseguradora")
        expected = [
            "Archivo",
            "Fecha Firma",
            "RUN Firmante",
            "Nombre Firmante",
            "REP Nº",
            "PROTOCOLIZADO Nº",
        ]
        for col in expected:
            assert col in spec["csv_columns"]