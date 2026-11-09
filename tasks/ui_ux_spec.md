# Spec: Refactorización GUI a PySide6

## Objective
App "Extractor de Metadatos PDF" — herramienta desktop interna para 1–2 auditores en Windows, en español.
Motivo: GUI Tkinter actual tosca/poco atractiva. Refactor a PySide6 siguiendo buenas prácticas PyQt6 (MVC señales/slots, QSS global, QThread, layouts).
No cambia: lógica de extracción (pipeline.py, batch.py, extraction/, csv_writer.py); CLI intacto.

Mejoras UIX priorizadas:
1. Layout paneles redimensionables (QSplitter)
2. Estados visuales por fila EXITO/ADVERTENCIA/ERROR
3. Iconos/branding (toolbar, ventana, versión)
4. Barra de progreso integrada (statusbar)
5. Atajos (F5=ejecutar, Esc=cancelar)
DnD: solo carpetas.

## Tech Stack
- Python ≥3.10 (venv 3.12.8)
- PySide6≥6.7 (API Signal/Slot, LGPL)
- PyInstaller≥6 (onefile)
- pytest-qt (dev)
- Deps actuales: PyMuPDF, pydantic, pandas, ruff

## Commands
Install:    pip install -e ".[dev]" PySide6 pytest-qt pyinstaller
GUI dev:    python -m extract_info.gui
Tests:      pytest
GUI tests:  pytest tests/test_gui/test_qt -q
Lint:       ruff check . && ruff format --check .
Build exe:  pyinstaller extract_info.spec --noconfirm

## Project Structure
extract_info/
  pipelines/           ← movido desde gui/nodes/
    base.py, registry.py, retail.py, aseguradora.py
  gui/
    __main__.py        # entry QApplication + QSS + MainWindow
    app.py             # MainWindow(QMainWindow)
    theme.py           # load_qss(), tokens, fuentes
    worker.py          # PDFWorker(QObject) → QThread + señales
    widgets/
      drop_zone.py     # QFrame#dropArea DnD carpetas
      results_table.py # QTableView + proxy model + delegate estados
      filter_panel.py
      log_viewer.py    # QPlainTextEdit dark + autosave JSON
extract_info.spec      # PyInstaller onefile + icon
tests/
  test_gui/test_pipelines.py
  test_gui/test_qt/

## Code Style
- Docstrings ES, type hints, f-strings, ruff select=["E","F","I","N","W"], line-length 100, py310
- Iron Laws PyQt6 skill: señales/slots UI↔lógica, QSS global (app.setStyleSheet), layouts (no geometría absoluta), worker en QThread sin tocar widgets, DPI-aware
- QSS fuente: assets/styles/style.QSS (carga única en QApplication)

## Testing Strategy
- pytest núcleo (~85 tests) + ruff
- pytest-qt: test_mainwindow_opens, test_worker_signals, test_proxy_model_sort_filter, test_drop_zone
- Checklist manual Windows: drop→run→pausa→cancel→export→logs

## Boundaries
Always: pytest+ruff antes de commit; QSS global; señales worker; layouts; contraste WCAG≥4.5:1; textos ES; extracción sin cambios
Ask first: nuevas deps; entrypoints; borrar Tkinter; tocar extraction/; config empaquetado/icono
Never: bloquear hilo principal; estilos inline; coordenadas absolutas; acceder widgets desde hilos; commitear builds; romper tests

## Success Criteria
1. python -m extract_info.gui abre sin Tkinter (Win+macOS dev)
2. Paridad: DnD/selector, Run/Pausa/Cancel, filtros, Export CSV UTF-8 BOM, log autosave
3. QSplitter persistente (tabla+logs+info)
4. Filas coloreadas EXITO/ADVERTENCIA/ERROR + leyenda
5. QProgressBar statusbar solo por señal (sin polling)
6. F5 ejecuta, Esc solicita cancelar
7. Iconos estándar Qt + windowIcon + título versión/pipeline
8. pyinstaller spec onefile → .exe funcional Windows

## Decisiones Cerradas
- Paleta/Estilos: assets/styles/style.QSS (crema #FDF4D2, primario #B0CDE6, secundario #A290B7, alerta #946D6D, texto #2C2626/#5A5252)
- Empaquetado: onefile (--onefile)
- Temas: solo claro
- Icono: assets/extract_info.ico
- Tkinter: eliminar al final tras validar .exe