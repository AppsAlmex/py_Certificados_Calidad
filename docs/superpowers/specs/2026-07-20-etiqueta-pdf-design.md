# Etiqueta PDF (3x2") — Diseño

Fecha: 2026-07-20

## Objetivo

Agregar una forma más de trabajo: una pestaña nueva en la ventana principal con
un formulario para generar un PDF de **etiqueta de 3 pulgadas (ancho) x 2
pulgadas (alto)**, usando una plantilla HTML editable (mismo patrón que los
certificados). Motor de render local (Chromium/Playwright), sin Oracle.

## Decisiones (acordadas)

- **Contenido:** solo texto (sin código de barras ni QR).
- **Datos:** captura manual; `FECHA` se autocompleta con la hora actual (editable);
  la empresa es fija en la plantilla.
- **Salida:** solo guardar el PDF en la carpeta `output`.

## Campos

| Campo | Editable | Default |
|-------|----------|---------|
| Empresa | no (constante en template) | ALMIDONES MEXICANOS S.A. DE C.V. |
| Cliente, Sucursal, Producto, Transporte, Lote, Equipo | sí | vacío |
| Fecha | sí | ahora, formato `dd/mm/aaaa HH:MM` |

## Arquitectura (reusa patrón data/layout/render existente)

- **`certificados/labels.py`** (nuevo)
  - `EMPRESA` constante.
  - `@dataclass LabelData`: cliente, sucursal, producto, transporte, lote,
    equipo, fecha, empresa. `__post_init__` pone `fecha = ahora` si viene vacía.
  - `render_label_html(data, templates_dir=LAYOUTS_DIR) -> str`: Jinja2 con
    global `asset()` (reusa `asset_data_uri` de pdf_renderer).
  - `render_label_pdf(data) -> bytes`: llama `html_to_pdf` con tamaño 3x2" y
    margen 0.
- **`certificados/layouts/etiqueta.html`** (nuevo): plantilla editable,
  `@page { size: 3in 2in; margin: 0 }`, campos desde `{{ d }}`.
- **`certificados/pdf_renderer.py`** (modificado):
  - Extraer `asset_data_uri(assets_dir, name) -> str` a nivel módulo; que
    `HtmlLayoutRenderer._asset_uri` la use (reuso, sin duplicar).
  - `html_to_pdf(html, page_format="Letter", *, width=None, height=None,
    margin=None)`: si `width` y `height` vienen, usa tamaño exacto en vez de
    `format`. Compatible hacia atrás (certificados siguen en Letter).
- **`certificados/__init__.py`**: exportar `LabelData`, `render_label_pdf`.
- **`gui/controller.py`**: `generate_label(campos: dict) -> Path`. Construye
  `LabelData`, renderiza, guarda en `output_dir` como
  `etiqueta_<lote_saneado>_<YYYYmmdd_HHMMSS>.pdf`, devuelve la ruta.
- **`gui/app.py`**: pestaña nueva **"Etiqueta"** con el formulario, botón
  "Generar PDF" (corre en hilo para no congelar) y etiqueta de estado. Al
  terminar muestra la ruta del PDF generado.

## Manejo de errores

- Render/guardado en hilo; excepción → estado + `messagebox.showerror` con el
  detalle, sin cerrar la app.
- Lote vacío → nombre de archivo cae en `etiqueta_etiqueta_<timestamp>.pdf`.

## Testing

- `LabelData`: empresa fija por defecto; fecha auto no vacía con formato correcto.
- `render_label_html`: contiene los valores de los campos y la empresa.
- `html_to_pdf`: con `width`/`height` arma los kwargs de tamaño (mock del
  objeto page, sin Chromium real — igual que los tests existentes usan fakes).
```
```
