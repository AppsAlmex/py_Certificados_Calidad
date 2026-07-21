"""Etiquetas de 3x2 pulgadas a partir de una plantilla HTML editable.

Mismo patron que los certificados (data/layout/render) pero standalone: los
datos se capturan a mano en la GUI, no se jalan de Oracle. El motor de render es
siempre local (Chromium via Playwright).

Para editar el diseno solo tocas ``certificados/layouts/etiqueta.html``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .exceptions import LayoutError
from .pdf_renderer import LAYOUTS_DIR, asset_data_uri, html_to_pdf

# Empresa fija en la etiqueta (no editable desde el formulario).
EMPRESA = "ALMIDONES MEXICANOS S.A. DE C.V."
LABEL_TEMPLATE = "etiqueta.html"
# Tamano fisico de la etiqueta.
LABEL_WIDTH = "3in"
LABEL_HEIGHT = "2in"
LABEL_MARGIN = {"top": "0", "bottom": "0", "left": "0", "right": "0"}

_DATE_FORMAT = "%d/%m/%Y %H:%M"


@dataclass
class LabelData:
    """Datos de una etiqueta. ``fecha`` vacia se autocompleta con la hora actual."""
    cliente: str = ""
    sucursal: str = ""
    producto: str = ""
    transporte: str = ""
    lote: str = ""
    equipo: str = ""
    fecha: str = ""
    empresa: str = EMPRESA

    def __post_init__(self) -> None:
        if not self.fecha:
            self.fecha = datetime.now().strftime(_DATE_FORMAT)


def _env(templates_dir) -> Environment:
    assets_dir = Path(templates_dir) / "assets"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["asset"] = lambda name: asset_data_uri(assets_dir, name)
    return env


def render_label_html(data: LabelData, templates_dir=LAYOUTS_DIR) -> str:
    """Renderiza el HTML de la etiqueta con los datos (sin generar PDF)."""
    template_path = Path(templates_dir) / LABEL_TEMPLATE
    if not template_path.exists():
        raise LayoutError(f"No existe la plantilla de etiqueta: {template_path}")
    return _env(templates_dir).get_template(LABEL_TEMPLATE).render(d=data)


def render_label_pdf(data: LabelData, templates_dir=LAYOUTS_DIR) -> bytes:
    """Genera el PDF (3x2", sin margenes) de la etiqueta."""
    html = render_label_html(data, templates_dir)
    return html_to_pdf(html, width=LABEL_WIDTH, height=LABEL_HEIGHT, margin=LABEL_MARGIN)
