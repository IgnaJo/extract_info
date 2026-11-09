"""Widgets reutilizables para la GUI (PySide6)."""

from extract_info.gui.widgets.drop_zone import DropZone
from extract_info.gui.widgets.filter_panel import FilterPanel
from extract_info.gui.widgets.log_viewer import LogViewer
from extract_info.gui.widgets.results_table import (
    ResultRowDelegate,
    ResultSortFilterProxyModel,
    ResultTableModel,
)

__all__ = [
    "DropZone",
    "FilterPanel",
    "LogViewer",
    "ResultTableModel",
    "ResultSortFilterProxyModel",
    "ResultRowDelegate",
]
