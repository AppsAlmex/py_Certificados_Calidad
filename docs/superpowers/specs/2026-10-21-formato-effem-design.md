# Diseño: Formato EFFEM (disclaimer de codificación del cliente)

Fecha: 2026-10-21
Branch: `feature/formato-effem`

## Problema

El cliente EFFEM pide que sus certificados incluyan la codificación que ellos
mismos usan (materiales GRD y sitios receptores aprobados). El layout de Oracle
BI Publisher **no se puede modificar por ahora**, así que el cambio debe vivir
enteramente en esta app (datos + plantillas HTML), no en Oracle.

El bloque de codificación es **texto fijo (disclaimer)**: el mismo en todos los
certificados EFFEM, no se calcula por embarque y no depende de ningún dato del
XML.

## Decisiones tomadas (brainstorming)

- Mostrar **material GRD + sitio receptor** como contenido, pero en forma de
  **bloque completo fijo** (los 3 materiales y todos los sitios), como disclaimer.
- Selección del formato **por cliente** (`NOMBRE_CLIENTE` del XML), no por un
  nuevo selector en Oracle ni en el CSV de batch (el cliente no viaja en el CSV;
  regresa en el XML tras ejecutar el reporte).
- Ubicación: **debajo de la tabla de info**, no dentro de la celda chica de
  `NO. DE PARTE CLIENTE` (una tabla no cabe ahí). El campo `NO. DE PARTE CLIENTE`
  sigue mostrando `d.parte_cliente` del XML sin cambios.
- El **resolver vive en el renderer** (`HtmlLayoutRenderer`), que ya es quien
  elige la plantilla.

## Arquitectura

### 1. Selección cliente → formato (catálogo CSV + resolver)

Nuevo catálogo `catalogos/cliente_formato.csv` (mismo patrón que
`formato.csv` / `planta.csv` / `inspector.csv`):

```
cliente,formato
EFFEM,EFFEM
```

Decisión: loader propio y explícito en `catalogs.py`,
`load_cliente_formato(path) -> dict[str, str]`, que lee encabezados
`cliente,formato` y devuelve `{cliente_normalizado: formato}`. Se prefiere
sobre reusar `load_catalog` (que exige columna `valor`) por legibilidad: los
encabezados dicen lo que son. Reutiliza el helper `_read_text` de `catalogs.py`
para tolerar la codificación de Excel (cp1252/UTF-8), igual que los demás CSV.

Resolver en `HtmlLayoutRenderer`:

- Al renderizar, antes de elegir plantilla, normaliza `d.cliente`
  (mayúsculas, sin acentos, trim) y busca si **contiene** alguna llave del
  catálogo (match por substring normalizado, case-insensitive).
- Si hay match → usa ese `formato` (ej. `EFFEM`) para elegir la plantilla.
- Si no hay match → usa `d.formato` actual (comportamiento intacto).

El renderer recibe el catálogo por inyección (parámetro opcional en el
constructor, default: lee `catalogos/cliente_formato.csv` si existe). Así no se
hardcodea "EFFEM" en el código y agregar un cliente nuevo es una fila CSV.

Match por substring porque `NOMBRE_CLIENTE` es texto libre de Oracle (ej.
"EFFEM MEXICO S.A. DE C.V."), no el literal "EFFEM".

### 2. Estructura de plantillas (herencia Jinja)

- `certificados/layouts/formato1.html` se vuelve **base**: se añade
  `{% block disclaimer %}{% endblock %}` (vacío) **debajo de la tabla `.info`**.
  Cero cambio visual para los formatos existentes.
- `certificados/layouts/formatoEFFEM.html`:
  ```jinja
  {% extends "formato1.html" %}
  {% block disclaimer %} ...tabla de codificación EFFEM... {% endblock %}
  ```
  ~15 líneas. El layout real no se duplica; un arreglo en `formato1.html` lo
  heredan todos.

El motor ya soporta herencia (Jinja `FileSystemLoader` en `pdf_renderer.py`),
no se necesita código Python para la herencia. `available_local_formats()`
detectará `formatoEFFEM` automáticamente (regex `formato(.+)\.html`).

### 3. Contenido del bloque (fijo)

Tabla "GRD Material / Approved receiving sites":

| GRD Material | Approved receiving sites |
|---|---|
| 1181898 / 1101419 — Glucose 63DE Syrup | ADM Cedar Rapids 80001247 · ADM Marshall 80001251 |
| 1104072 — High Maltose Glucose Syrup | Almidones Mexicanos 80003229 · ADM Cedar Rapids 80001247 · ADM Marshall 80001251 |
| 1148993 — High Fructose Glucose Syrup | ADM Cedar Rapids 80001247 · ADM Clinton 80004006 · ADM Columbus 80003710 |

Estilo consistente con las tablas existentes (`.info` / `.params`). Título del
bloque: "CODIFICACIÓN CLIENTE (EFFEM)".

## Flujo de datos

1. Batch genera el certificado; Oracle devuelve el XML con `NOMBRE_CLIENTE`.
2. `parse_certificate` produce `CertificateData` (sin cambios).
3. `HtmlLayoutRenderer.render`:
   - resolver: `d.cliente` contiene "EFFEM" → formato efectivo = `EFFEM`.
   - elige `formatoEFFEM.html` → extiende `formato1.html` + bloque disclaimer.
4. PDF resultante = layout estándar + tabla de codificación EFFEM debajo de info.

## Manejo de errores

- CSV ausente → sin overrides, todo usa `d.formato` (no es error, igual que los
  otros catálogos).
- Formato resuelto sin plantilla (`formatoEFFEM.html` no existe) → el
  `template_name` actual ya lanza `LayoutError` con mensaje claro.

## Pruebas

- `cliente_formato`: resuelve "EFFEM MEXICO…" → `EFFEM`; cliente no listado →
  respeta `d.formato`; CSV ausente → sin override.
- Match normalizado: acentos/mayúsculas/substring.
- Render `formatoEFFEM` contiene los 3 materiales GRD y los códigos de sitio
  (80001247, 80001251, 80003229, 80004006, 80003710).
- Regresión: cliente no-EFFEM renderiza `formato1` sin el bloque disclaimer.
- Herencia: `formato1.html` sigue renderizando igual (bloque vacío no afecta).

## Fuera de alcance (YAGNI)

- Resolver material/sitio dinámico por producto/destino (se descartó: es
  disclaimer fijo).
- UI para editar el bloque (es texto fijo en la plantilla).
- Cambios en el layout de Oracle.