# Plan: Refactorización GUI a PySide6

## Resumen de decisiones
| Tema | Decisión |
|---|---|
| Framework | PySide6 (LGPL, Signal/Slot, buenas prácticas PyQt6 skill) |
| Paleta/Estilos | assets/styles/style.QSS (carga global QApplication) |
| Empaquetado | onefile (--onefile) |
| Temas | Solo claro |
| Icono | assets/extract_info.ico |
| Tkinter | Eliminar al final |

## Arquitectura MVC objetivo
(ver spec)

## Fases y orden

### Fase 0 — Baseline & Refactor dominio (sin UI)
0.1 Crear extract_info/pipelines/ copiando gui/nodes/ → imports internos actualizados
0.2 Actualizar gui/app.py y gui/widgets/log_viewer.py imports a extract_info.pipelines
0.3 Renombrar tests/test_gui/test_nodes.py → test_pipelines.py, fix imports
0.4 Añadir PySide6, pytest-qt, pyinstaller a [project.optional-dependencies].dev en pyproject.toml

Verificación: pytest tests/test_gui/test_pipelines.py -q ✅

### Fase 1 — Scaffold GUI PySide6 (paridad 1:1)
1.1 gui/theme.py: load_qss(app) lee assets/styles/style.QSS + aplica + fuentes Segoe UI
1.2 gui/worker.py: PDFWorker(QObject) con señales progress(int,int,str), completed(object), failed(str)
1.3 gui/app.py: MainWindow(QMainWindow) — toolbar, menú, statusbar con QProgressBar, QSplitter vertical
1.4 widgets/drop_zone.py: DropZone(QFrame)#dropArea dragEnter/dropEvent carpetas + property dragActive
1.5 widgets/results_table.py: ResultTableModel(QAbstractTableModel) + ResultSortFilterProxyModel + delegate estados
1.6 widgets/filter_panel.py: FilterPanel(QWidget) emite filters_changed(dict) → proxy model
1.7 widgets/log_viewer.py: LogViewer(QPlainTextEdit) estilo dark + add_log + save_to_json
1.8 gui/__main__.py: QApplication + load_qss + MainWindow + app.exec()

Verificación: python -m extract_info.gui abre app funcional completa

### Fase 2 — Mejoras UIX (orden prioridad)
2.1 Paneles redimensionables: QSplitter persistente (QSettings save/restore sizes)
2.2 Estados visuales: ResultRowDelegate pinta fondo/texto/icono por row["estado"] + leyenda statusbar
2.3 Iconos/Branding: QStyle estándar (SP_MediaPlay, SP_MediaPause, SP_DialogCancelButton, SP_DialogSaveButton, SP_FileDialogContentsView) + windowIcon + título versión/pipeline
2.4 Barra progreso integrada: QProgressBar statusbar permanente actualizada solo por señal progress
2.5 Atajos: QShortcut(F5, run), QShortcut(Escape, request_cancel)

### Fase 3 — Empaquetado, Testing, Limpieza
3.1 extract_info.spec onefile: icon=assets/extract_info.ico, hiddenimports, datas
3.2 Tests pytest-qt: test_mainwindow, test_worker_signals, test_proxy_model, test_drop_zone
3.3 Prueba manual completa Windows: drop→run→pausa→cancel→export→logs
3.4 Eliminar Tkinter: borrar gui/app.py viejo, gui/widgets/* tkinter, gui/theme.py tkinter, gui/nodes/, gui/__main__.py tkinter, tkinterdnd2 deps

Verificación final: .exe onefile corre en Windows limpio y procesa carpeta prueba

## Riesgos y mitigaciones
| Riesgo | Mitigación |
|---|---|
| onefile lento/antivirus | Probar en Windows destino; fallback onedir (1 línea .spec) |
| QSS widgets no cubiertos | Añadir selectores extra según necesidad |
| Señales cross-thread | Worker solo emite; slot hilo principal actualiza modelo |
| Migración nodes rompe CLI | Verificar CLI tras Fase 0 (no debería, usa pipeline.py) |
| DPI Windows | HighDpiScaleFactorRoundingPolicy.PassThrough + AA_EnableHighDpiScaling |

## Paralelización
- Secuencial: 0 → 1.1 → 1.2 → 1.3 → (1.4–1.7 cualquier orden) → 1.8 → 2.x orden → 3.x orden
- Paralelizable: 1.4, 1.5, 1.6, 1.7 independientes

## Checkpoints
| Hito | Comando |
|---|---|
| Fase 0 | pytest tests/test_gui/test_pipelines.py -q |
| Fase 1.8 | python -m extract_info.gui (funcional completo) |
| Fase 2.5 | Atajos, paneles, estados, progreso sin polling |
| Fase 3.3 | .exe onefile Windows limpio procesa carpeta prueba |