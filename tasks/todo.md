# Todo: Refactorización GUI a PySide6

## Fase 0 — Baseline & Refactor dominio
- [ ] T0.1: Crear extract_info/pipelines/ copiando gui/nodes/ (base, registry, retail, aseguradora)
  - Acceptance: Archivos copiados, imports internos relativos funcionan
  - Verify: python -c "from extract_info.pipelines.base import list_nodes; print(list_nodes())"
  - Files: extract_info/pipelines/*.py (nuevos)

- [ ] T0.2: Actualizar imports en gui/app.py y gui/widgets/log_viewer.py a extract_info.pipelines
  - Acceptance: No imports de extract_info.gui.nodes
  - Verify: grep -r "extract_info.gui.nodes" extract_info/gui/ (debe dar 0)
  - Files: extract_info/gui/app.py, extract_info/gui/widgets/log_viewer.py

- [ ] T0.3: Renombrar tests/test_gui/test_nodes.py → test_pipelines.py, fix imports
  - Acceptance: Tests pasan con nuevos imports
  - Verify: pytest tests/test_gui/test_pipelines.py -q
  - Files: tests/test_gui/test_pipelines.py (renombrado)

- [ ] T0.4: Añadir PySide6, pytest-qt, pyinstaller a pyproject.toml [project.optional-dependencies].dev
  - Acceptance: pip install -e ".[dev]" instala todo
  - Verify: pip list | grep -E "PySide6|pytest-qt|pyinstaller"
  - Files: pyproject.toml

## Fase 1 — Scaffold GUI PySide6
- [ ] T1.1: gui/theme.py con load_qss(app) → lee assets/styles/style.QSS + setStyleSheet
  - Acceptance: Ventana abre con fondo crema, tabla blanca, headers morados
  - Verify: python -c "from extract_info.gui.theme import load_qss; from PySide6.QtWidgets import QApplication; app=QApplication([]); load_qss(app); print('OK')"
  - Files: extract_info/gui/theme.py

- [ ] T1.2: gui/worker.py — PDFWorker(QObject) con señales progress/completed/failed + run()
  - Acceptance: Worker corre en QThread, emite señales queued sin bloquear UI
  - Verify: test pytest-qt test_worker_signals (ver T3.2)
  - Files: extract_info/gui/worker.py

- [ ] T1.3: gui/app.py — MainWindow(QMainWindow) base: toolbar, menú, statusbar+QProgressBar, QSplitter
  - Acceptance: Ventana con layout base redimensionable
  - Verify: python -m extract_info.gui (abre, layout visible)
  - Files: extract_info/gui/app.py

- [ ] T1.4: widgets/drop_zone.py — DropZone(QFrame)#dropArea DnD carpetas + dragActive
  - Acceptance: Arrastrar carpeta resalta; soltar emite folder_selected(str)
  - Verify: test pytest-qt test_drop_zone
  - Files: extract_info/gui/widgets/drop_zone.py

- [ ] T1.5: widgets/results_table.py — Modelo + proxy + delegate estados
  - Acceptance: Tabla muestra datos, ordena, filtra, filas coloreadas por estado
  - Verify: test pytest-qt test_proxy_model_sort_filter
  - Files: extract_info/gui/widgets/results_table.py

- [ ] T1.6: widgets/filter_panel.py — FilterPanel emite filters_changed(dict)
  - Acceptance: Filtros aplicados a proxy, tabla se reduce
  - Verify: test pytest-qt test_filter_panel
  - Files: extract_info/gui/widgets/filter_panel.py

- [ ] T1.7: widgets/log_viewer.py — LogViewer(QPlainTextEdit) dark + add_log + save_to_json
  - Acceptance: Logs aparecen, se guardan JSON en extract_info/logs/
  - Verify: test pytest-qt test_log_viewer
  - Files: extract_info/gui/widgets/log_viewer.py

- [ ] T1.8: gui/__main__.py — entry QApplication + load_qss + MainWindow
  - Acceptance: python -m extract_info.gui abre app funcional completa
  - Verify: python -m extract_info.gui (run manual completo)
  - Files: extract_info/gui/__main__.py

## Fase 2 — Mejoras UIX
- [ ] T2.1: Paneles redimensionables persistentes (QSettings save/restore splitter sizes)
  - Acceptance: Tamaño paneles se restaura entre ejecuciones
  - Verify: Cerrar/abrir app → splitter sizes iguales
  - Files: extract_info/gui/app.py

- [ ] T2.2: Estados visuales — ResultRowDelegate pinta por row["estado"] + leyenda
  - Acceptance: Filas verde/ámbar/rojo + tooltip + leyenda statusbar
  - Verify: test pytest-qt test_row_delegate + manual
  - Files: extract_info/gui/widgets/results_table.py

- [ ] T2.3: Iconos/Branding — QStyle estándar + windowIcon + título versión/pipeline
  - Acceptance: Botones con iconos, ventana con ícono, título descriptivo
  - Verify: Manual visual
  - Files: extract_info/gui/app.py, extract_info/gui/widgets/*.py

- [ ] T2.4: Barra progreso statusbar — QProgressBar permanente actualizada por señal
  - Acceptance: Sin polling; progreso fluido + label "Procesando X/Y: archivo"
  - Verify: test pytest-qt test_progress_bar + manual
  - Files: extract_info/gui/app.py, extract_info/gui/worker.py

- [ ] T2.5: Atajos — QShortcut(F5, run), QShortcut(Escape, request_cancel)
  - Acceptance: F5 ejecuta, Esc abre diálogo cancelar
  - Verify: Manual teclado
  - Files: extract_info/gui/app.py

## Fase 3 — Empaquetado, Testing, Limpieza
- [ ] T3.1: extract_info.spec onefile con icon=assets/extract_info.ico, hiddenimports
  - Acceptance: pyinstaller spec genera dist/extract_info.exe
  - Verify: pyinstaller extract_info.spec --noconfirm && ./dist/extract_info.exe --help
  - Files: extract_info.spec

- [ ] T3.2: Tests pytest-qt en tests/test_gui/test_qt/
  - Acceptance: test_mainwindow, test_worker_signals, test_proxy_model_sort_filter, test_drop_zone pasan
  - Verify: pytest tests/test_gui/test_qt -v
  - Files: tests/test_gui/test_qt/*.py (4 archivos)

- [ ] T3.3: Prueba manual completa Windows (checklist)
  - Acceptance: Drop→Run→Pausa→Cancel→Export→Logs OK
  - Verify: Checklist manual en máquina Windows
  - Files: (ninguno)

- [ ] T3.4: Eliminar código Tkinter (app.py viejo, widgets/, theme.py, nodes/, __main__.py, tkinterdnd2)
  - Acceptance: Repo sin Tkinter; python -m extract_info.gui usa solo PySide6
  - Verify: grep -r "tkinter" extract_info/ (0 resultados); pytest pasa
  - Files: Múltiples (borrado)