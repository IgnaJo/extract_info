"""Ventana principal de la aplicación (PySide6)."""

from __future__ import annotations

import csv
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, QSize, Qt, QThread, Slot
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


from extract_info.gui.widgets.drop_zone import DropZone
from extract_info.gui.widgets.filter_panel import FilterPanel
from extract_info.gui.widgets.log_viewer import LogViewer
from extract_info.gui.widgets.results_table import (
    ResultRowDelegate,
    ResultSortFilterProxyModel,
    ResultTableModel,
    configure_headers,
)
from extract_info.gui.worker import PDFWorker
from extract_info.pipelines.base import LogEntry, NodeResult, NODE_SPECS, list_nodes, get_node_spec
from extract_info.pipelines.retail import retail_process_folder
from extract_info.pipelines.aseguradora import aseguradora_process_folder


class MainWindow(QMainWindow):
    """Ventana principal con toolbar, menú, statusbar y layout con QSplitter."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Extractor de Metadatos PDF v1.0.0")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        # Icono de ventana
        icon_path = Path(__file__).resolve().parents[2] / "assets" / "extract_info.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Estado
        self._current_node_name: Optional[str] = None
        self._current_result: Optional[NodeResult] = None
        self._is_processing = False
        self._cancel_flag = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Inicialmente NO pausado
        self._last_folder = os.path.expanduser("~")

        # Worker
        self._worker: Optional[PDFWorker] = None
        self._worker_thread = None

        # Nodos disponibles (ya registrados en NODE_SPECS)
        # NodeRegistry.discover() ya no necesario

        # Configurar UI
        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()
        self._update_action_buttons()

    def _setup_ui(self) -> None:
        # Widget central con layout vertical
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Header con selector de pipeline
        main_layout.addWidget(self._create_header())

        # Drop zone
        self.drop_zone = DropZone(
            on_drop_callback=self._on_folder_selected,
            on_clear_callback=self._on_selection_cleared,
        )
        main_layout.addWidget(self.drop_zone)

        # Action bar (botones Ejecutar/Pausar/Cancelar/Exportar)
        main_layout.addWidget(self._create_action_bar())

        # Panel de filtros
        node_names = list_nodes()
        self.filter_panel = FilterPanel(node_names=node_names)
        self.filter_panel.filters_changed.connect(self._on_filter_change)
        # Sincronizar selector de pipeline del filter panel con el header
        self.filter_panel._pipeline_combo.currentTextChanged.connect(self._on_node_change_from_filter)
        main_layout.addWidget(self.filter_panel)

        # QSplitter principal: tabla arriba, logs+info abajo
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(self.splitter, stretch=1)

        # Parte superior: tabla de resultados
        self.results_table = self._create_results_table()
        self.splitter.addWidget(self.results_table)

        # Parte inferior: logs + info
        bottom_widget = self._create_bottom_panel()
        self.splitter.addWidget(bottom_widget)

        # Proporciones iniciales del splitter (70% tabla, 30% logs)
        self.splitter.setSizes([500, 200])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

        # Status bar con barra de progreso
        self._setup_statusbar()

    def _create_header(self) -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        # Título
        title = QLabel("Extractor de Metadatos PDF")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2C2626;")
        layout.addWidget(title)

        # Selector de pipeline
        node_layout = QVBoxLayout()
        node_layout.addWidget(QLabel("Pipeline:"))
        self.combo_node = QComboBox()
        self.combo_node.addItems(list_nodes())
        self.combo_node.currentTextChanged.connect(self._on_node_change)
        self.combo_node.setMinimumWidth(200)
        node_layout.addWidget(self.combo_node)

        # Añadir al layout principal horizontal
        from PySide6.QtWidgets import QHBoxLayout
        main_h = QHBoxLayout()
        main_h.addWidget(title)
        main_h.addStretch()
        main_h.addLayout(node_layout)
        header.setLayout(main_h)

        if self.combo_node.count() > 0:
            self._current_node_name = self.combo_node.currentText()
            # El modelo se creará después en _create_results_table
            # Guardamos el nombre del nodo inicial para aplicarlo luego
            self._initial_node_name = self.combo_node.currentText()

        return header

    def _create_action_bar(self) -> QWidget:
        bar = QWidget()
        from PySide6.QtWidgets import QHBoxLayout
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        style = self.style()

        # Ejecutar
        self.btn_run = QPushButton(" Ejecutar")
        self.btn_run.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_run.setObjectName("btnRun")
        self.btn_run.clicked.connect(self._start_processing)
        layout.addWidget(self.btn_run)

        # Pausar / Reanudar
        self.btn_pause = QPushButton(" Pausar")
        self.btn_pause.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.btn_pause.setObjectName("btnPause")
        self.btn_pause.clicked.connect(self._on_pause_toggle)
        layout.addWidget(self.btn_pause)

        # Cancelar
        self.btn_cancel = QPushButton(" Cancelar")
        self.btn_cancel.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        self.btn_cancel.setObjectName("btnDanger")
        self.btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(self.btn_cancel)

        # Separador
        from PySide6.QtWidgets import QFrame
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # Exportar CSV
        self.btn_export = QPushButton(" Exportar CSV")
        self.btn_export.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_export.clicked.connect(self._export_csv)
        layout.addWidget(self.btn_export)

        # Estado (derecha)
        self.action_status = QLabel("Selecciona una carpeta para comenzar")
        self.action_status.setStyleSheet("color: #5A5252; font-size: 9pt;")
        layout.addStretch()
        layout.addWidget(self.action_status)

        return bar

    def _create_results_table(self) -> QWidget:
        from PySide6.QtWidgets import QTableView, QVBoxLayout, QWidget

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table_model = ResultTableModel()
        self._proxy_model = ResultSortFilterProxyModel()
        self._proxy_model.setSourceModel(self._table_model)

        self._table_view = QTableView()
        self._table_view.setModel(self._proxy_model)
        self._table_view.setItemDelegate(ResultRowDelegate())
        self._table_view.setSortingEnabled(True)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        configure_headers(self._table_view)
        self._table_view.verticalHeader().setVisible(False)

        # Aplicar columnas del nodo inicial si existe
        if hasattr(self, "_initial_node_name") and self._initial_node_name:
            spec = get_node_spec(self._initial_node_name)
            if spec:
                self._table_model.set_columns(spec["csv_columns"])
                self._current_node_name = spec["name"]
            delattr(self, "_initial_node_name")

        layout.addWidget(self._table_view)
        return widget

    def _create_bottom_panel(self) -> QWidget:
        from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

        bottom = QWidget()
        layout = QHBoxLayout(bottom)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Logs (izquierda)
        self.log_viewer = LogViewer()
        layout.addWidget(self.log_viewer, stretch=1)

        # Info panel (derecha)
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        self.progress_label = QLabel("Listo")
        self.progress_label.setStyleSheet("color: #5A5252; font-size: 9pt;")
        info_layout.addWidget(self.progress_label)

        layout.addWidget(info, stretch=0)

        return bottom

    def _setup_statusbar(self) -> None:
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Leyenda de estados (izquierda) - inline from _create_legend_widget
        from PySide6.QtWidgets import QHBoxLayout
        legend = QWidget()
        legend_layout = QHBoxLayout(legend)
        legend_layout.setContentsMargins(8, 0, 8, 0)
        legend_layout.setSpacing(12)
        legend_layout.addWidget(QLabel("Estados:"))
        legend_layout.addWidget(QLabel("● EXITO", styleSheet="color: #166534; font-size: 8pt;"))
        legend_layout.addWidget(QLabel("● ADVERTENCIA", styleSheet="color: #92400e; font-size: 8pt;"))
        legend_layout.addWidget(QLabel("● ERROR", styleSheet="color: #991b1b; font-size: 8pt;"))
        self._legend_widget = legend
        self.statusbar.addWidget(self._legend_widget)

        # Barra de progreso permanente en statusbar (derecha)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMinimumWidth(150)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m")
        self.progress_bar.hide()

        self.statusbar.addPermanentWidget(self.progress_bar)

    def _setup_menu(self) -> None:
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # Archivo
        file_menu = QMenu("Archivo", self)
        menubar.addMenu(file_menu)

        act_select = QAction("Seleccionar carpeta...", self)
        act_select.setShortcut(QKeySequence.StandardKey.Open)
        act_select.triggered.connect(self._select_folder)
        file_menu.addAction(act_select)

        file_menu.addSeparator()

        act_exit = QAction("Salir", self)
        act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Ayuda
        help_menu = QMenu("Ayuda", self)
        menubar.addMenu(help_menu)

        act_about = QAction("Acerca de", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _setup_shortcuts(self) -> None:
        # F5 = Ejecutar
        shortcut_run = QShortcut(QKeySequence(Qt.Key.Key_F5), self)
        shortcut_run.activated.connect(self._start_processing)

        # Esc = Cancelar
        shortcut_cancel = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        shortcut_cancel.activated.connect(self._request_cancel)

        # Restore settings (inline _restore_settings)
        settings = QSettings("ExtractInfo", "ExtractorPDF")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        splitter_sizes = settings.value("splitterSizes")
        if splitter_sizes:
            self.splitter.setSizes([int(x) for x in splitter_sizes])

    def closeEvent(self, event) -> None:
        # Save settings (inline _save_settings)
        settings = QSettings("ExtractInfo", "ExtractorPDF")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("splitterSizes", self.splitter.sizes())

        if self._worker_thread and self._worker_thread.isRunning():
            self._cancel_flag = True
            self._pause_event.set()
            self._worker_thread.quit()
            self._worker_thread.wait(2000)
        super().closeEvent(event)

    # --- Slots de UI ---

    def _on_node_change(self, node_name: str) -> None:
        spec = get_node_spec(node_name)
        if spec:
            self._table_model.set_columns(spec["csv_columns"])
            self._table_model.clear()
            self._current_result = None
            self._current_node_name = spec["name"]
            self._update_action_buttons()

            self.log_viewer.add_log(LogEntry(
                timestamp=datetime.now().isoformat(),
                level="INFO",
                message=f"Nodo seleccionado: {spec['name']}",
                node_name=spec["name"],
            ))

            # Sincronizar combo del header si la señal viene del filter panel
            if self.combo_node.currentText() != node_name:
                self.combo_node.blockSignals(True)
                self.combo_node.setCurrentText(node_name)
                self.combo_node.blockSignals(False)

    def _on_node_change_from_filter(self, node_name: str) -> None:
        """Maneja cambio de nodo desde el filter panel (sincroniza header)."""
        self._on_node_change(node_name)

    def _on_folder_selected(self, path: str) -> None:
        self._last_folder = path if os.path.isdir(path) else os.path.dirname(path)
        self._update_action_buttons()

    def _on_selection_cleared(self) -> None:
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        has_path = self.drop_zone.get_selected_path() is not None

        if self._is_processing:
            self.btn_run.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            self.btn_export.setEnabled(False)
            self.drop_zone.setEnabled(False)
            self.combo_node.setEnabled(False)
        else:
            self.btn_run.setEnabled(has_path)
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            has_result = self._current_result is not None and len(self._current_result.rows) > 0
            self.btn_export.setEnabled(has_result)
            self.drop_zone.setEnabled(True)
            self.combo_node.setEnabled(True)

    def _start_processing(self) -> None:
        path = self.drop_zone.get_selected_path()
        if not path:
            QMessageBox.warning(self, "Sin selección", "Selecciona una carpeta primero.")
            return

        if not hasattr(self, '_current_node_name') or not self._current_node_name:
            QMessageBox.critical(self, "Error", "Selecciona un pipeline primero.")
            return

        self._is_processing = True
        self._cancel_flag = False
        self._pause_event.set()
        self._update_action_buttons()
        self.action_status.setText("Procesando...")

        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.show()

        # Crear worker (inline create_worker factory)
        self._worker = PDFWorker(
            self._current_node_name,
            path,
            self._pause_event,
            lambda: self._cancel_flag,
        )
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_processing_complete)
        self._worker.failed.connect(self._on_processing_error)
        # Cleanup
        self._worker.completed.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker.completed.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)

        self._worker_thread.start()

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, filename: str) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        state = "⏸ Pausado" if not self._pause_event.is_set() else "Procesando"
        self.progress_label.setText(f"{state} {current}/{total}: {filename}")

    @Slot(object)
    def _on_processing_complete(self, result: NodeResult) -> None:
        self._is_processing = False
        self._current_result = result
        self._pause_event.set()

        self._table_model.set_data(result.rows)
        self.filter_panel.update_folder_list(
            sorted(
                {row["nombre_carpeta"] for row in result.rows if row.get("nombre_carpeta")}
            )
        )
        self.log_viewer.add_logs(result.logs)

        self._update_action_buttons()
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.hide()

        self.progress_label.setText(
            f"Completado: {result.total_processed} archivos "
            f"({result.success_count} OK, {result.warning_count} warnings, "
            f"{result.error_count} errores)"
        )
        self.action_status.setText("Proceso completado")

    @Slot(str)
    def _on_processing_error(self, error_msg: str) -> None:
        self._is_processing = False
        self._pause_event.set()
        self._update_action_buttons()
        self.progress_label.setText("Error en procesamiento")
        self.progress_bar.hide()
        self.action_status.setText("Error")
        QMessageBox.critical(self, "Error de procesamiento", f"Ocurrió un error:\n{error_msg}")

    def _on_pause_toggle(self) -> None:
        if self._pause_event.is_set():
            self._pause_event.clear()
            self.btn_pause.setText("▶ Reanudar")
            self.action_status.setText("⏸ Pausado")
        else:
            self._pause_event.set()
            self.btn_pause.setText("⏸ Pausar")
            self.action_status.setText("Procesando...")

    def _on_cancel(self) -> None:
        if QMessageBox.question(
            self,
            "Cancelar procesamiento",
            "¿Estás seguro de que deseas cancelar?\n\nSe perderán los archivos no procesados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self._cancel_flag = True
            self._pause_event.set()  # Liberar pausa para que el loop pueda salir
            self.action_status.setText("Cancelando...")

    def _request_cancel(self) -> None:
        """Invocado por atajo Esc."""
        if self._is_processing:
            self._on_cancel()

    def _on_filter_change(self, filters: dict) -> None:
        self._proxy_model.set_folder_filter(filters.get("folder", ""))
        self._proxy_model.set_estado_filter(filters.get("estado", ""))
        self._proxy_model.set_text_filter(filters.get("text", ""))

    def _export_csv(self) -> None:
        if not self._current_result or not self._current_result.rows:
            QMessageBox.warning(self, "Sin datos", "No hay resultados para exportar.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"resultado_{self._current_node_name}_{timestamp}.csv"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar CSV",
            default_name,
            "CSV (*.csv);;Todos los archivos (*.*)",
        )

        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self._current_result.columns,
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(self._current_result.rows)

            QMessageBox.information(
                self,
                "Exportación exitosa",
                f"CSV generado:\n{filepath}\n\nRegistros: {len(self._current_result.rows)}",
            )

            self.log_viewer.add_log(LogEntry(
                timestamp=datetime.now().isoformat(),
                level="INFO",
                message=f"CSV exportado: {filepath}",
                node_name=self._current_node_name,
            ))

        except Exception as e:
            QMessageBox.critical(self, "Error de exportación", f"Error al guardar el CSV:\n{e}")

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecciona la carpeta con PDFs",
            self._last_folder,
        )
        if folder:
            self._last_folder = folder
            self.drop_zone._set_selected_path(folder)

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "Acerca de",
            "Extractor de Metadatos PDF\n\n"
            "Versión: 1.0.0\n"
            f"Pipeline actual: {self._current_node_name if hasattr(self, '_current_node_name') and self._current_node_name else 'Ninguno'}\n\n"
            "Nodos disponibles:\n"
            + "\n".join(f"  - {name}" for name in list_nodes()),
        )