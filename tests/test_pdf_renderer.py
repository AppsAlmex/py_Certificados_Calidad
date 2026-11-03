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
