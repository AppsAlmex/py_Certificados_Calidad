"""Tests de la generacion de etiquetas (HTML + tamano PDF), sin Chromium real."""
import re

import pytest

from certificados import labels
from certificados.labels import EMPRESA, LabelData, render_label_html
from certificados.exceptions import LayoutError


# --- LabelData --------------------------------------------------------------
def test_empresa_por_defecto():
    d = LabelData()
    assert d.empresa == EMPRESA


def test_fecha_auto_cuando_vacia():
    d = LabelData()
    # formato dd/mm/aaaa HH:MM
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", d.fecha)


def test_fecha_respeta_valor_dado():
    d = LabelData(fecha="01/01/2020 08:00")
    assert d.fecha == "01/01/2020 08:00"


# --- render_label_html ------------------------------------------------------
def test_html_incluye_los_campos():
    d = LabelData(
        cliente="CORPORATIVO DESTILERIA SANTA LUCIA",
        sucursal="LAS AGUJAS",
        producto="100-005-201-DEXTROSA SIX M|GRANEL",
        transporte="OUTBOUND.TEATSA",
        lote="AI_ALM_GDL_02-941636",
        equipo="P_TEATSA_12-TA",
        fecha="20/07/2026 16:35",
    )
    html = render_label_html(d)
    assert EMPRESA in html
    assert "CORPORATIVO DESTILERIA SANTA LUCIA" in html
    assert "LAS AGUJAS" in html
    assert "AI_ALM_GDL_02-941636" in html
    assert "P_TEATSA_12-TA" in html
    assert "20/07/2026 16:35" in html
    # el pipe del producto se escapa como entidad HTML (autoescape)
    assert "DEXTROSA SIX M" in html


def test_html_escapa_contenido():
    d = LabelData(cliente="<script>x</script>")
    html = render_label_html(d)
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_plantilla_ausente_lanza(tmp_path):
    with pytest.raises(LayoutError):
        render_label_html(LabelData(), templates_dir=tmp_path)


# --- render_label_pdf pasa el tamano correcto a html_to_pdf -----------------
def test_render_pdf_usa_tamano_3x2(monkeypatch):
    captured = {}

    def fake_html_to_pdf(html, page_format="Letter", *, width=None, height=None, margin=None):
        captured.update(html=html, width=width, height=height, margin=margin)
        return b"%PDF-fake"

    monkeypatch.setattr(labels, "html_to_pdf", fake_html_to_pdf)
    out = labels.render_label_pdf(LabelData(lote="X1"))
    assert out == b"%PDF-fake"
    assert captured["width"] == "3in"
    assert captured["height"] == "2in"
    assert captured["margin"] == {"top": "0", "bottom": "0", "left": "0", "right": "0"}
    assert "X1" in captured["html"]
