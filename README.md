# Motor de Extracción PDF a CSV

CLI + GUI para extracción de metadatos desde archivos PDF heterogéneos de auditoría/contratos.
Procesa carpetas de PDFs recursivamente, extrae campos clave mediante pipeline modular,
y genera un CSV por carpeta contenedora.

## Requisitos

**Runtime (CLI)**

- Python 3.10+
- `PyMuPDF` (fitz)
- `pydantic` ≥ 2.0

**GUI (opcional)**

- `PySide6` ≥ 6.7

**Tests**

- `pytest` ≥ 7.0
- `pytest-qt` ≥ 4.2 (solo tests de GUI)
- `pandas` ≥ 2.0

## Instalación

```bash
# Solo CLI
pip install -r requirements.txt

# CLI + GUI + testing
pip install -e ".[dev]"
```

## Uso CLI

```bash
# Ejecución básica
python -m extract_info --input /carpeta/pdfs --output /carpeta/salida

# Elegir pipeline (retail por defecto)
python -m extract_info --input /carpeta/pdfs --output /carpeta/salida --pipeline aseguradora

# Modo verbose/debug
python -m extract_info --input /carpeta/pdfs --output /carpeta/salida --verbose

# Con número de procesos paralelos
python -m extract_info --input /carpeta/pdfs --output /carpeta/salida --workers 4

# Un único CSV unificado en lugar de un CSV por carpeta
python -m extract_info --input /carpeta/pdfs --output /carpeta/salida --unified

# Help
python -m extract_info --help
```

## Uso GUI (PySide6)

```bash
# Lanzar interfaz gráfica
python -m extract_info.gui
```

**Características GUI:**
- Drag & drop de carpetas con PDFs
- Selector de pipeline (Retail / Aseguradora)
- Barra de progreso en tiempo real
- Tabla de resultados con ordenamiento y filtros (carpeta, estado, texto)
- Estados visuales por fila: 🟢 EXITO · 🟡 ADVERTENCIA · 🔴 ERROR
- Panel de logs con autoguardado JSON
- Exportación CSV (UTF-8 BOM)
- Atajos: **F5** = Ejecutar · **Esc** = Cancelar
- Ventana y paneles redimensionables (estado persistente)

## Campos extraídos

### Pipeline Retail (contratos tarjeta crédito)

| Campo | Origen | Descripción |
|---|---|---|
| `nombre_archivo` | Metadatos | Nombre del PDF sin extensión |
| `nombre_completo` | Ancla "Nombre completo:" | Texto extraído del campo nombre |
| `rut` | Ancla "RUT:" | RUT chileno validado (`X.XXX.XXX-X`) |
| `fecha_contrato` | Ancla "Vigentes al" / "Fecha" | Fecha normalizada `dd-mm-yyyy` |
| `proto` | Ancla "PROTOCOLIZADO N°" | Número de protocolizado |
| `repertorio` | Ancla "REP N°" | Número de repertorio |
| `fecha_repertorio` | Mismo bloque que repertorio | Fecha de asignación `dd-mm-yyyy` |
| `cantidad_hojas` | Propiedades del PDF | Total de páginas |
| `nombre_carpeta` | Estructura de directorios | Nombre de la carpeta contenedora |
| `estado_extraccion` | Calculado | `EXITO`, `ADVERTENCIA` o `ERROR` |
| `observaciones` | Calculado | Detalle de campos faltantes o errores |

### Pipeline Aseguradora (documentos notariales)

| Campo | Origen |
|---|---|
| `Archivo` | Nombre del archivo |
| `Fecha Firma` | Penúltima página (regex) |
| `RUN Firmante` | Penúltima página (regex) |
| `Nombre Firmante` | Penúltima página (regex) |
| `REP Nº` | Página 1, coordenadas fijas |
| `PROTOCOLIZADO Nº` | Página 1, coordenadas fijas |
| `REP Fecha` | Página 1, coordenadas fijas |
| `Cantidad de páginas` | Propiedades del PDF |
| `Estado` | Calculado (`OK` / `REVISAR: ...`) |

Los nombres de columna son el contrato del CSV con la base general: no se renombran por estética. La tabla de la GUI muestra etiquetas cortas (`nombre_completo` → "Nombre Completo", `PROTOCOLIZADO Nº` → "Nº Proto") definidas en `HEADER_LABELS`; el CSV exportado conserva siempre los nombres canónicos.

## Pipeline de Extracción

El motor funciona mediante una tubería modular de 4 etapas:

1. **Ingesta y Limpieza**: PyMuPDF extrae texto ordenado por coordenadas espaciales
2. **Búsqueda por Anclajes**: Búsqueda de etiquetas conceptuales + ventana adyacente
3. **Refinamiento Regex**: Patrones estrictos para validar formatos
4. **Validación Pydantic**: Esquema tipado; los campos no encontrados quedan en `None`

## Estructura del Proyecto

```
extract_info/
├── extract_info/
│   ├── __init__.py
│   ├── __main__.py               # Entry point CLI
│   ├── models.py                 # Pydantic schemas
│   ├── pipeline.py               # Orquestador del pipeline
│   ├── batch.py                  # Escaneo recursivo + ProcessPoolExecutor
│   ├── csv_writer.py             # Exportación CSV por carpeta
│   ├── pipelines/                # Nodos de extracción (lógica de dominio)
│   │   ├── __init__.py
│   │   ├── base.py               # BaseNode abstracto + dataclasses + list_nodes()
│   │   ├── retail.py             # Pipeline contratos retail
│   │   └── aseguradora.py        # Pipeline aseguradora (coordenadas)
│   ├── gui/                      # Interfaz gráfica PySide6
│   │   ├── __init__.py
│   │   ├── __main__.py           # Entry point GUI + carga del QSS global
│   │   ├── app.py                # MainWindow (QMainWindow)
│   │   ├── worker.py             # PDFWorker (QThread + señales)
│   │   └── widgets/
│   │       ├── drop_zone.py      # DnD carpetas
│   │       ├── results_table.py  # Modelo + proxy + delegate
│   │       ├── filter_panel.py   # Filtros dinámicos
│   │       └── log_viewer.py     # Logs dark + autosave JSON
│   └── extraction/
│       ├── text_reader.py        # Extracción PyMuPDF
│       ├── file_discovery.py     # Descubrimiento de PDFs en carpetas
│       ├── anchors.py            # Búsqueda por anclajes
│       ├── patterns.py           # Patrones regex
│       └── validators.py         # Validación de campos
├── assets/
│   ├── *.pdf                     # PDFs de muestra para pruebas
│   ├── styles/
│   │   └── style.QSS             # Hoja de estilos global
│   └── extract_info.ico          # Icono aplicación
├── tests/
│   ├── test_models.py
│   ├── test_patterns.py
│   ├── test_text_reader.py
│   ├── test_anchors.py
│   ├── test_validators.py
│   ├── test_pipeline.py
│   ├── test_batch.py
│   ├── test_csv_writer.py
│   ├── test_assets.py
│   ├── test_file_discovery.py
│   ├── test_scrambled.py
│   └── test_gui/
│       ├── test_pipelines.py     # Tests nodos de pipelines
│       └── test_qt/              # Tests pytest-qt
│           ├── test_mainwindow.py
│           ├── test_worker.py
│           ├── test_model.py
│           └── test_dropzone.py
├── tasks/
│   ├── ui_ux_spec.md             # Spec refactorización GUI
│   ├── plan.md                   # Plan de implementación
│   └── todo.md                   # Lista de tareas
├── extract_info.spec             # PyInstaller spec (onefile)
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Validación de Estados

| Estado | Condición |
|---|---|
| `EXITO` / `OK` | Todos los campos presentes y con formato correcto |
| `ADVERTENCIA` / `REVISAR` | Campos faltantes o formato inválido |
| `ERROR` | Error al procesar el archivo |

Los campos que no se encuentran **no se rellenan con valores por defecto**: quedan en `None`
en el modelo y como celda vacía en el CSV. El `estado` es la única señal de que falta algo.

## Testing

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Solo tests GUI (pytest-qt)
pytest tests/test_gui/test_qt/ -v

# Con cobertura
pytest tests/ -v --cov=extract_info --cov-report=term-missing

# Lint
ruff check extract_info/ tests/
ruff format extract_info/ tests/
```

## Empaquetado (PyInstaller)

```bash
# Generar .exe onefile (Windows)
pyinstaller extract_info.spec --noconfirm

# El ejecutable estará en dist/extract_info.exe
```

## Salida

Los CSVs se generan con codificación `UTF-8 BOM` (`utf-8-sig`) para compatibilidad directa
con Microsoft Excel en sistemas con configuración regional en español.

Un archivo CSV independiente por cada carpeta contenedora procesada:
`resultado_<nombre_carpeta>.csv`

Con `--unified` (`-u`) se genera un único CSV consolidado con todos los documentos
(`resultado_unificado.csv`).

El pipeline se elige con `--pipeline` (`-p`): `retail` (default) o `aseguradora`.
Las columnas del CSV dependen del pipeline elegido.

## Licencia

Uso interno organizacional.