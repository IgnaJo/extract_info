"""Tests para el sistema de nodos."""

import pytest

from extract_info.gui.nodes.base import BaseNode, LogEntry, NodeResult
from extract_info.gui.nodes.registry import NodeRegistry


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


class TestNodeRegistry:
    """Tests para el registry de nodos."""

    def setup_method(self):
        """Limpia el registry antes de cada test."""
        NodeRegistry.clear()

    def test_discover_nodes(self):
        """Discover encuentra nodos disponibles."""
        NodeRegistry.discover()
        nodes = NodeRegistry.list_nodes()
        assert "Retail" in nodes
        assert "Aseguradora" in nodes

    def test_get_node(self):
        """get_node retorna instancia del nodo."""
        NodeRegistry.discover()
        node = NodeRegistry.get_node("Retail")
        assert node is not None
        assert node.name == "Retail"

    def test_get_node_returns_same_instance(self):
        """get_node retorna la misma instancia (singleton)."""
        NodeRegistry.discover()
        node1 = NodeRegistry.get_node("Retail")
        node2 = NodeRegistry.get_node("Retail")
        assert node1 is node2

    def test_get_nonexistent_node(self):
        """get_node retorna None para nodo inexistente."""
        NodeRegistry.discover()
        node = NodeRegistry.get_node("NonExistent")
        assert node is None

    def test_list_nodes_sorted(self):
        """list_nodes retorna nodos ordenados."""
        NodeRegistry.discover()
        nodes = NodeRegistry.list_nodes()
        assert nodes == sorted(nodes)


class TestRetailNode:
    """Tests para el nodo Retail."""

    def setup_method(self):
        """Configura el nodo Retail."""
        NodeRegistry.discover()
        self.node = NodeRegistry.get_node("Retail")

    def test_node_properties(self):
        """RetailNode tiene las propiedades correctas."""
        assert self.node.name == "Retail"
        assert len(self.node.description) > 0
        assert len(self.node.csv_columns) > 0

    def test_csv_columns(self):
        """RetailNode tiene las columnas esperadas."""
        expected = [
            "nombre_archivo",
            "nombre_completo",
            "rut",
            "fecha_contrato",
        ]
        for col in expected:
            assert col in self.node.csv_columns


class TestAseguradoraNode:
    """Tests para el nodo Aseguradora."""

    def setup_method(self):
        """Configura el nodo Aseguradora."""
        NodeRegistry.discover()
        self.node = NodeRegistry.get_node("Aseguradora")

    def test_node_properties(self):
        """AseguradoraNode tiene las propiedades correctas."""
        assert self.node.name == "Aseguradora"
        assert len(self.node.csv_columns) > 0

    def test_csv_columns(self):
        """AseguradoraNode tiene las columnas del Extractor.py original."""
        expected = [
            "Archivo",
            "Fecha Firma",
            "RUN Firmante",
            "Nombre Firmante",
            "PROTOCOLIZADO Nº",
        ]
        for col in expected:
            assert col in self.node.csv_columns
