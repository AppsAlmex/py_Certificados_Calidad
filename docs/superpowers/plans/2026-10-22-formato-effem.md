# Formato EFFEM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que los certificados del cliente EFFEM muestren un bloque fijo de codificación (materiales GRD + sitios receptores aprobados) debajo de la tabla de info, seleccionando la plantilla automáticamente por el cliente del XML.

**Architecture:** La plantilla `formato1.html` se vuelve base con un `{% block disclaimer %}`; `formatoEFFEM.html` la hereda y solo llena ese bloque. El `HtmlLayoutRenderer` resuelve la plantilla efectiva con un override por cliente leído de `catalogos/cliente_formato.csv` (match por substring normalizado de `NOMBRE_CLIENTE`); si no hay match usa `d.formato` como siempre.

**Tech Stack:** Python 3, Jinja2 (herencia de plantillas), lxml (ya en uso), pytest.

## Global Constraints

- El layout de Oracle NO se modifica: el cambio vive solo en esta app (Python + HTML).
- No hardcodear "EFFEM" en código: el cliente→formato vive en CSV.
- Los demás formatos/clientes deben renderizar EXACTAMENTE igual que hoy.
- CSV de catálogos tolera codificación Excel (cp1252 / UTF-8 con y sin BOM) vía `_read_text` existente en `catalogs.py`.
- Patrón de tests: pytest con `tmp_path`, estilo de `tests/test_catalogs.py`.

---

### Task 1: Loader `load_cliente_formato` + `normalize_cliente`

**Files:**
- Modify: `certificados/catalogs.py` (agregar función de normalización y loader)
- Test: `tests/test_catalogs.py` (agregar tests al final)

**Interfaces:**
- Produces:
  - `normalize_cliente(text: str) -> str` — mayúsculas, sin acentos, trim.
  - `load_cliente_formato(path: str | Path) -> Dict[str, str]` — devuelve `{cliente_normalizado: formato}`. Archivo ausente → `{}`. Falta columna `cliente` o `formato` → `CatalogError`.

- [ ] **Step 1: Write the failing tests**

En `tests/test_catalogs.py`, agregar al final:

```python
from certificados.catalogs import load_cliente_formato, normalize_cliente


def test_normalize_cliente_upper_trim_accents():
    assert normalize_cliente("  Éffem México  ") == "EFFEM MEXICO"
    assert normalize_cliente("") == ""


def test_load_cliente_formato_basico(tmp_path):
    path = write(tmp_path, "cliente,formato\nEFFEM,EFFEM\n", name="cf.csv")
    assert load_cliente_formato(path) == {"EFFEM": "EFFEM"}


def test_load_cliente_formato_normaliza_llave(tmp_path):
    path = write(tmp_path, "cliente,formato\néffem,EFFEM\n", name="cf.csv")
    assert load_cliente_formato(path) == {"EFFEM": "EFFEM"}


def test_load_cliente_formato_missing_file(tmp_path):
    assert load_cliente_formato(tmp_path / "no.csv") == {}


def test_load_cliente_formato_filas_incompletas_ignoradas(tmp_path):
    path = write(tmp_path, "cliente,formato\nEFFEM,EFFEM\n,X\nACME,\n", name="cf.csv")
    assert load_cliente_formato(path) == {"EFFEM": "EFFEM"}


def test_load_cliente_formato_falta_columna(tmp_path):
    path = write(tmp_path, "cliente,descripcion\nEFFEM,x\n", name="cf.csv")
    with pytest.raises(CatalogError, match="formato"):
        load_cliente_formato(path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_catalogs.py -k "cliente_formato or normalize_cliente" -v`
Expected: FAIL con `ImportError: cannot import name 'load_cliente_formato'`.

- [ ] **Step 3: Implement**

En `certificados/catalogs.py`, agregar `import unicodedata` arriba (junto a los otros imports) y al final del archivo:

```python
def normalize_cliente(text: str) -> str:
    """Normaliza un nombre de cliente para comparar: mayusculas, sin acentos, trim."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_acentos.upper().strip()


def load_cliente_formato(path: str | Path) -> dict[str, str]:
    """Lee un CSV ``cliente,formato`` -> ``{cliente_normalizado: formato}``.

    Archivo ausente -> {} (no es error, el campo simplemente no tiene overrides).
    Falta columna 'cliente' o 'formato' -> CatalogError.
    """
    file = Path(path)
    if not file.exists():
        return {}
    reader = csv.DictReader(io.StringIO(_read_text(file)))
    headers = [(h or "").strip().lower() for h in (reader.fieldnames or [])]
    if "cliente" not in headers or "formato" not in headers:
        raise CatalogError(
            f"El catalogo {file} debe tener columnas 'cliente' y 'formato'"
        )
    mapping: dict[str, str] = {}
    for row in reader:
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        cliente = norm.get("cliente", "")
        formato = norm.get("formato", "")
        if not cliente or not formato:
            continue
        mapping[normalize_cliente(cliente)] = formato
    return mapping
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_catalogs.py -k "cliente_formato or normalize_cliente" -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add certificados/catalogs.py tests/test_catalogs.py
git commit -m "feat: loader cliente_formato y normalize_cliente"
```

---

### Task 2: Resolver de formato por cliente en el renderer

**Files:**
- Modify: `certificados/pdf_renderer.py` (import, constructor, método `resolve_formato`, uso en `render_html`)
- Test: `tests/test_pdf_renderer.py` (NUEVO archivo)

**Interfaces:**
- Consumes: `load_cliente_formato`, `normalize_cliente` (Task 1).
- Produces:
  - `HtmlLayoutRenderer(__init__)` acepta nuevo kwarg `cliente_formato: dict[str, str] | None = None`. Si es `None`, carga `app_dir()/catalogos/cliente_formato.csv`.
  - `HtmlLayoutRenderer.resolve_formato(data: CertificateData) -> str` — devuelve el formato override si `normalize_cliente(data.cliente)` contiene alguna llave del catálogo; si no, `data.formato`.

- [ ] **Step 1: Write the failing tests**

Crear `tests/test_pdf_renderer.py`:

```python
from certificados.certificate_data import CertificateData
from certificados.pdf_renderer import HtmlLayoutRenderer


def test_resolver_override_por_cliente():
    r = HtmlLayoutRenderer(cliente_formato={"EFFEM": "EFFEM"})
    d = CertificateData(formato="1", cliente="EFFEM MEXICO S.A. DE C.V.")
    assert r.resolve_formato(d) == "EFFEM"


def test_resolver_default_sin_match():
    r = HtmlLayoutRenderer(cliente_formato={"EFFEM": "EFFEM"})
    d = CertificateData(formato="1", cliente="EMBOTELLADORA")
    assert r.resolve_formato(d) == "1"


def test_resolver_catalogo_vacio():
    r = HtmlLayoutRenderer(cliente_formato={})
    d = CertificateData(formato="1", cliente="EFFEM")
    assert r.resolve_formato(d) == "1"


def test_resolver_ignora_acentos_y_mayusculas():
    r = HtmlLayoutRenderer(cliente_formato={"EFFEM": "EFFEM"})
    d = CertificateData(formato="1", cliente="éffem s.a.")
    assert r.resolve_formato(d) == "EFFEM"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pdf_renderer.py -v`
Expected: FAIL con `TypeError: __init__() got an unexpected keyword argument 'cliente_formato'`.

- [ ] **Step 3: Implement**

En `certificados/pdf_renderer.py`:

Agregar el import de catalogs cerca de los otros imports locales:

```python
from .catalogs import load_cliente_formato, normalize_cliente
```

Reemplazar el `__init__` de `HtmlLayoutRenderer` para aceptar el catálogo:

```python
    def __init__(self, templates_dir=LAYOUTS_DIR, assets_dir=None, page_format: str = "Letter",
                 cliente_formato: dict[str, str] | None = None):
        self.templates_dir = Path(templates_dir)
        self.assets_dir = Path(assets_dir) if assets_dir else self.templates_dir / "assets"
        self.page_format = page_format
        if cliente_formato is None:
            cliente_formato = load_cliente_formato(app_dir() / "catalogos" / "cliente_formato.csv")
        self.cliente_formato = cliente_formato
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        # Disponible en las plantillas: {{ asset('logo.png') }} -> data URI.
        self._env.globals["asset"] = self._asset_uri
```

`app_dir` ya se importa de `.runtime` al inicio del módulo (`from .runtime import app_dir, is_frozen, resource_dir`); verifica que siga ahí.

Agregar el método resolver (debajo de `template_name`):

```python
    def resolve_formato(self, data: CertificateData) -> str:
        """Formato efectivo: override por cliente si aplica; si no, el del XML."""
        cliente_norm = normalize_cliente(data.cliente)
        for llave, formato in self.cliente_formato.items():
            if llave and llave in cliente_norm:
                return formato
        return data.formato
```

Cambiar `render_html` para usar el resolver:

```python
    def render_html(self, data: CertificateData) -> str:
        template = self._env.get_template(self.template_name(self.resolve_formato(data)))
        return template.render(d=data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pdf_renderer.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add certificados/pdf_renderer.py tests/test_pdf_renderer.py
git commit -m "feat: resolver de formato por cliente en HtmlLayoutRenderer"
```

---

### Task 3: Plantilla EFFEM (herencia) + catálogo + render e2e

**Files:**
- Modify: `certificados/layouts/formato1.html` (agregar `{% block disclaimer %}` debajo de la tabla `.info`)
- Create: `certificados/layouts/formatoEFFEM.html`
- Create: `catalogos/cliente_formato.csv`
- Test: `tests/test_pdf_renderer.py` (agregar tests de render)

**Interfaces:**
- Consumes: `resolve_formato` + `render_html` (Task 2), plantilla base (este task).
- Produces: `formatoEFFEM.html` detectable por `available_local_formats()` (regex `formato(.+)\.html`).

- [ ] **Step 1: Write the failing tests**

En `tests/test_pdf_renderer.py`, agregar:

```python
def test_effem_render_contiene_codificacion():
    r = HtmlLayoutRenderer(cliente_formato={"EFFEM": "EFFEM"})
    d = CertificateData(formato="1", cliente="EFFEM MEXICO")
    html = r.render_html(d)
    for code in ("1181898", "1101419", "1104072", "1148993",
                 "80001247", "80001251", "80003229", "80004006", "80003710"):
        assert code in html, f"falta {code}"
    assert "CODIFICACI" in html  # titulo del disclaimer


def test_no_effem_sin_disclaimer():
    r = HtmlLayoutRenderer(cliente_formato={"EFFEM": "EFFEM"})
    d = CertificateData(formato="1", cliente="EMBOTELLADORA")
    html = r.render_html(d)
    assert "80003229" not in html
    assert "High Maltose" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pdf_renderer.py -k "effem or disclaimer" -v`
Expected: FAIL — `test_effem_render_contiene_codificacion` lanza `LayoutError` (no existe `formatoEFFEM.html`).

- [ ] **Step 3: Agregar el bloque en la plantilla base**

En `certificados/layouts/formato1.html`, localizar el cierre de la tabla `.info` (la línea `</table>` que sigue a la fila de `LOTE` / `PLANTA PRODUCTORA`, antes de `<table class="params">`). Insertar el bloque entre ambas tablas:

```html
  </table>

  {% block disclaimer %}{% endblock %}

  <table class="params">
```

(No cambia nada visual para formatos que no llenan el bloque.)

- [ ] **Step 4: Crear la plantilla EFFEM**

Crear `certificados/layouts/formatoEFFEM.html`:

```html
{% extends "formato1.html" %}
{#
  Formato EFFEM = formato1 + bloque de codificacion del cliente (disclaimer fijo).
  Se selecciona automaticamente cuando NOMBRE_CLIENTE contiene "EFFEM"
  (ver catalogos/cliente_formato.csv y HtmlLayoutRenderer.resolve_formato).
#}
{% block disclaimer %}
  <table class="info" style="margin-top:10px;">
    <tr>
      <td class="lbl" colspan="2" style="text-align:center;">CODIFICACIÓN CLIENTE (EFFEM)</td>
    </tr>
    <tr>
      <td class="lbl" style="width:40%;">GRD Material</td>
      <td class="lbl">Approved receiving sites</td>
    </tr>
    <tr>
      <td class="val">1181898 / 1101419 — Glucose 63DE Syrup</td>
      <td class="val">ADM Cedar Rapids 80001247 · ADM Marshall 80001251</td>
    </tr>
    <tr>
      <td class="val">1104072 — High Maltose Glucose Syrup</td>
      <td class="val">Almidones Mexicanos 80003229 · ADM Cedar Rapids 80001247 · ADM Marshall 80001251</td>
    </tr>
    <tr>
      <td class="val">1148993 — High Fructose Glucose Syrup</td>
      <td class="val">ADM Cedar Rapids 80001247 · ADM Clinton 80004006 · ADM Columbus 80003710</td>
    </tr>
  </table>
{% endblock %}
```

- [ ] **Step 5: Crear el catálogo**

Crear `catalogos/cliente_formato.csv`:

```
cliente,formato
EFFEM,EFFEM
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_pdf_renderer.py -v`
Expected: PASS (6 tests: los 4 del resolver + los 2 de render).

- [ ] **Step 7: Regresión + suite completa**

Run: `python -m pytest -q`
Expected: toda la suite PASS (sin romper tests existentes de certificate_data, catalogs, pdf_engine).

- [ ] **Step 8: Commit**

```bash
git add certificados/layouts/formato1.html certificados/layouts/formatoEFFEM.html catalogos/cliente_formato.csv tests/test_pdf_renderer.py
git commit -m "feat: plantilla formatoEFFEM con disclaimer de codificacion"
```

---

## Verificación de aceptación (manual, requiere Oracle)

Correr el batch con `templates/template_EFFEM.csv` (embarque `1335761`). Verificar que el PDF:
1. Usa el layout estándar (formato1) con la tabla de codificación EFFEM debajo de la tabla de info.
2. Muestra los 3 materiales GRD y los 5 códigos de sitio.
3. `NO. DE PARTE CLIENTE` sigue mostrando el valor del XML.

Precondición: el embarque `1335761` debe traer `NOMBRE_CLIENTE` de EFFEM en el XML; si no, saldría formato1 sin disclaimer (el resolver no dispararía).
