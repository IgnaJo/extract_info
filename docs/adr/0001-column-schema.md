# 0001 — Esquema de columnas declarativo

**Estado:** aceptado · **Fecha:** 2026-11-14

Cada pipeline declara sus columnas con `ColumnSpec(key, label, kind)`. La tabla,
el delegate y los filtros leen esa metadata; `csv_columns` queda como lista
derivada de `key`. Ningún consumidor vuelve a hardcodear nombres de columna.

## Contexto

`NODE_SPECS` guardaba `csv_columns: list[str]`. La GUI ya reconstruía la tabla a
partir de esa lista, pero el **significado** de cada columna estaba repartido en
literales:

| Consumidor | Adivinaba por |
|---|---|
| `results_table.HEADER_LABELS` | diccionario global por nombre de columna |
| `ResultRowDelegate` | claves `"Estado"` / `"estado_extraccion"` |
| `ResultSortFilterProxyModel` | `"nombre_carpeta"`, `"Estado"`, `"estado_extraccion"` |
| `_create_error_row` | substrings `"archivo"`, `"estado"`, `"pagina"` |

Agregar un pipeline obligaba a editar cuatro archivos de la vista. Un olvido no
rompía tests: fallaba en runtime con columnas sin etiqueta, filtros inertes o
filas de error vacías.

## Decisión

Un único vocabulario compartido en `extract_info/columns.py`:

```python
class ColumnKind(str, Enum):
    TEXT, DATE, NUMBER, FILENAME, FOLDER, STATUS, NOTES

@dataclass(frozen=True)
class ColumnSpec:
    key: str
    label: str
    kind: ColumnKind = ColumnKind.TEXT
```

`NODE_SPECS[nodo]["columns"]` es la fuente de verdad. `csv_columns` se deriva:

```python
_spec["csv_columns"] = column_keys(_spec["columns"])
```

Los consumidores resuelven por `kind`:

- Etiqueta de cabecera → `ColumnSpec.label`.
- Color de fila y filtro de estado → columna con `kind is STATUS`.
- Filtro de carpeta → columna con `kind is FOLDER`.
- Fila de error → `FILENAME` recibe el archivo, `STATUS` recibe `ERROR: ...`,
  `NUMBER` recibe `0`, el resto `None`.

`process_folder` recibe `columns: Sequence[ColumnSpec]` y valida las claves de
cada fila contra el esquema; una clave desconocida se convierte en fila de error
con mensaje explícito en vez de reventar el `DictWriter` al exportar.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Esquema separado para CSV y para tabla | Duplica la verdad y deriva con el tiempo |
| Reflexión sobre los modelos pydantic | Frágil, acopla la vista a pydantic, no aporta sobre `ColumnSpec` |
| Un delegate por pipeline | Sobredimensionado para el problema real (colores por estado) |
| Dejar `csv_columns` como fuente y agregar solo etiquetas | No resuelve filtros, colores ni filas de error |

## Consecuencias

**Positivas**

- Agregar un pipeline no toca la vista: `NODE_SPECS` + módulo + registry.
- Etiquetas, filtros y colores son correctos por construcción.
- Una fila con columnas fuera de esquema falla temprano y con mensaje claro.
- El CSV no cambia: mismos headers, mismo orden.

**Límites aceptados**

- **Forma de la fila:** `process_single` devuelve un `dict` con exactamente las
  `key` declaradas. Es un contrato explícito, no algo a esconder.
- **Vocabulario de estado:** la vista sigue reconociendo `OK/EXITO`,
  `REVISAR/ADVERTENCIA`, `ERROR`. Normalizar Aseguradora a `EstadoExtraccion`
  es un cambio de extracción, fuera de este ADR.
- **Código legacy:** `csv_writer.CSV_COLUMNS`, `Extractor` batch
  (`batch.py:52`) y `AseguradoraNode._create_error_row` conservan su propio
  esquema Retail-only. No se migran acá.

## Migración aplicada

| Archivo | Cambio |
|---|---|
| `extract_info/columns.py` | nuevo: `ColumnKind`, `ColumnSpec`, `column_keys`, `find_kind` |
| `extract_info/pipelines/base.py` | `NODE_SPECS` usa `columns`; `csv_columns` derivado; `process_folder` y `_create_error_row` por `kind`; validación de claves |
| `extract_info/pipelines/retail.py`, `aseguradora.py` | pasan `columns=spec["columns"]` |
| `extract_info/gui/widgets/results_table.py` | sin `HEADER_LABELS`; modelo/proxy/delegate resuelven por `kind` con fallback legacy |
| `extract_info/gui/app.py` | `set_columns(spec["columns"])` |

## Criterios de aceptación

- [x] `pytest -q` verde y `ruff check .` limpio.
- [x] Los tests existentes que comparan `spec["csv_columns"]` siguen pasando.
- [x] `headerData` devuelve la etiqueta declarada (`Archivo`, `Hojas`, ...).
- [x] Una fila con clave no declarada produce fila de error, no excepción al exportar.
- [x] El export CSV mantiene headers y orden.

## Siguiente paso

Consolidar el dispatch `nombre → runner` en un único registry
(`PIPELINE_RUNNERS` / `NODE_RUNNERS`) para eliminar la duplicación entre
`batch.py` y `gui/worker.py`.
