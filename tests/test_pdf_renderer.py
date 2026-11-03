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
