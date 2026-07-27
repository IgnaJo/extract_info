# Motor de Extracción PDF a CSV

CLI para extracción de metadatos desde archivos PDF heterogéneos de auditoría/contratos.
Procesa carpetas de PDFs recursivamente, extrae campos clave mediante pipeline modular,
y genera un CSV por carpeta contenedora.

## Requisitos

- Python 3.10+
- `PyMuPDF` (fitz)
- `pydantic` ≥ 2.0
- `pandas` ≥ 2.0

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Ejecución básica
python -m extract_info --input /carpeta/pdfs --output /carpeta/salida

# Modo verbose/debug
python -m extract_info --input /carpeta/pdfs --output /carpeta/salida --verbose

# Con número de procesos paralelos
python -m extract_info --input /carpeta/pdfs --output /carpeta/salida --workers 4
```

## Campos extraídos

| Campo | Origen | Descripción |
|---|---|---|
| `nombre_archivo` | Metadatos del archivo | Nombre del PDF sin extensión |
| `nombre_completo` | Ancla "Nombre completo:" | Texto extraído del campo nombre |
| `rut` | Ancla "RUT:" | RUT chileno validado (formato `X.XXX.XXX-X`) |
| `fecha_contrato` | Ancla "Vigentes al" / "Fecha" | Fecha normalizada `dd-mm-yyyy` |
| `proto` | Ancla "PROTOCOLIZADO N°" | Número de protocolizado |
| `repertorio` | Ancla "REP N°" | Número de repertorio |
| `fecha_repertorio` | Mismo bloque que repertorio | Fecha de asignación `dd-mm-yyyy` |
| `cantidad_hojas` | Propiedades del PDF | Total de páginas |
| `nombre_carpeta` | Estructura de directorios | Nombre de la carpeta contenedora |
| `estado_extraccion` | Calculado | `EXITO`, `ADVERTENCIA` o `ERROR` |
| `observaciones` | Calculado | Detalle de campos faltantes o errores |

## Pipeline de Extracción

El motor funciona mediante una tubería modular de 4 etapas:

1. **Ingesta y Limpieza**: PyMuPDF extrae texto ordenado por coordenadas espaciales
2. **Búsqueda por Anclajes**: Búsqueda de etiquetas conceptuales + ventana adyacente
3. **Refinamiento Regex**: Patrones estrictos para validar formatos
4. **Validación Pydantic**: Esquema tipado con fallback rules

## Estructura del Proyecto

```
extract_info/
├── extract_info/
│   ├── __init__.py
│   ├── __main__.py           # Entry point CLI
│   ├── models.py             # Pydantic schemas
│   ├── pipeline.py           # Orquestador del pipeline
│   ├── batch.py              # Escaneo recursivo + ProcessPoolExecutor
│   ├── csv_writer.py         # Exportación CSV por carpeta
│   └── extraction/
│       ├── text_reader.py    # Extracción PyMuPDF
│       ├── anchors.py        # Búsqueda por anclajes
│       ├── patterns.py       # Patrones regex
│       └── validators.py     # Validación de campos
├── tests/
│   ├── test_models.py
│   ├── test_patterns.py
│   ├── test_text_reader.py
│   ├── test_anchors.py
│   ├── test_validators.py
│   ├── test_pipeline.py
│   ├── test_batch.py
│   └── test_csv_writer.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Validación de Estados

| Estado | Condición |
|---|---|
| `EXITO` | Todos los campos presentes y con formato correcto |
| `ADVERTENCIA` | Campos faltantes o formato inválido |
| `ERROR` | Error al procesar el archivo |

## Testing

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Con cobertura
pytest tests/ -v --cov=extract_info --cov-report=term-missing

# Lint
ruff check extract_info/ tests/
ruff format extract_info/ tests/
```

## Salida

Los CSVs se generan con codificación `UTF-8 BOM` (`utf-8-sig`) para compatibilidad directa
con Microsoft Excel en sistemas con configuración regional en español.

Un archivo CSV independiente por cada carpeta contenedora procesada:
`resultado_<nombre_carpeta>.csv`
