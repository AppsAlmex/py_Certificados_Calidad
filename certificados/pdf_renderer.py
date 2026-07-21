"""Render de PDF a partir de plantillas HTML (una por formato).

Separa la data del layout: recibe un ``CertificateData`` y una plantilla HTML
(editable, con CSS moderno) y produce el PDF con Chromium headless (Playwright),
que da fidelidad pixel-perfect.

Para agregar/editar un formato solo tocas ``certificados/layouts/formatoN.html``
y el CSS; no se toca este codigo (Open/Closed).
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from base64 import b64encode
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .certificate_data import CertificateData, parse_certificate
from .exceptions import LayoutError
from .runtime import app_dir, is_frozen, resource_dir


def _default_layouts_dir() -> Path:
    """layouts editable junto al .exe si existe; si no, el empaquetado."""
    packaged = Path(__file__).resolve().parent / "layouts"
    if is_frozen():
        external = app_dir() / "layouts"
        if external.is_dir():
            return external
        return resource_dir() / "certificados" / "layouts"
    return packaged


LAYOUTS_DIR = _default_layouts_dir()


def asset_data_uri(assets_dir, name: str) -> str:
    """Lee un asset (imagen) y lo devuelve como data URI base64 para embeberlo
    en el HTML. '' si no existe. Compartido por certificados y etiquetas."""
    file = Path(assets_dir) / name
    if not file.exists():
        return ""
    suffix = file.suffix.lower()
    mime = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".svg": "image/svg+xml",
    }.get(suffix, "application/octet-stream")
    return f"data:{mime};base64,{b64encode(file.read_bytes()).decode()}"


def available_local_formats(templates_dir=LAYOUTS_DIR) -> List[str]:
    """Formatos con plantilla local (archivos formato<X>.html). Ej: ['1']."""
    directory = Path(templates_dir)
    if not directory.exists():
        return []
    formatos = []
    for file in sorted(directory.glob("formato*.html")):
        match = re.fullmatch(r"formato(.+)\.html", file.name)
        if match:
            formatos.append(match.group(1))
    return formatos


class LayoutRenderer(ABC):
    """Abstraccion: de un CertificateData produce los bytes de un PDF."""

    @abstractmethod
    def render(self, data: CertificateData) -> bytes:
        ...


class HtmlLayoutRenderer(LayoutRenderer):
    def __init__(self, templates_dir=LAYOUTS_DIR, assets_dir=None, page_format: str = "Letter"):
        self.templates_dir = Path(templates_dir)
        self.assets_dir = Path(assets_dir) if assets_dir else self.templates_dir / "assets"
        self.page_format = page_format
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        # Disponible en las plantillas: {{ asset('logo.png') }} -> data URI.
        self._env.globals["asset"] = self._asset_uri

    def _asset_uri(self, name: str) -> str:
        return asset_data_uri(self.assets_dir, name)

    def template_name(self, formato: str) -> str:
        name = f"formato{formato}.html"
        if not (self.templates_dir / name).exists():
            disponibles = ", ".join(available_local_formats(self.templates_dir)) or "ninguno"
            raise LayoutError(
                f"No existe plantilla local para el formato '{formato}'. "
                f"Formatos con plantilla: {disponibles}"
            )
        return name

    def render_html(self, data: CertificateData) -> str:
        template = self._env.get_template(self.template_name(data.formato))
        return template.render(d=data)

    def render(self, data: CertificateData) -> bytes:
        return html_to_pdf(self.render_html(data), self.page_format)


def html_to_pdf(html: str, page_format: str = "Letter", *,
                width: str | None = None, height: str | None = None,
                margin: dict | None = None) -> bytes:
    """Convierte HTML en PDF con Chromium headless (Playwright, sincrono).

    Por defecto usa un tamaño de pagina nombrado (``page_format``, ej. Letter).
    Si se dan ``width`` y ``height`` (ej. "3in"/"2in") usa ese tamaño exacto en
    vez del formato -> util para etiquetas. ``margin`` sobreescribe los margenes
    (por defecto 10mm; para etiquetas conviene 0)."""
    from playwright.sync_api import sync_playwright

    if margin is None:
        margin = {"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"}
    size_kwargs = {"width": width, "height": height} if (width and height) else {"format": page_format}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            pdf = page.pdf(print_background=True, margin=margin, **size_kwargs)
        finally:
            browser.close()
    return pdf


def render_from_xml(xml: bytes | str, **kwargs) -> bytes:
    """Atajo: XML del data model -> PDF."""
    return HtmlLayoutRenderer(**kwargs).render(parse_certificate(xml))
