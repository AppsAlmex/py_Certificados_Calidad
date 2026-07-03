from certificados.certificate_data import parse_certificate
from certificados.pdf_renderer import HtmlLayoutRenderer

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<DATA_DS><P_FORMATO>1</P_FORMATO>
<LIST_G_DATOS_GENERALES><G_DATOS_GENERALES>
<ALMIDONES_MEXICANOS>ALMIDONES MEXICANOS S.A. DE C.V.</ALMIDONES_MEXICANOS>
<LUGAR_EXPEDICION>GUADALAJARA</LUGAR_EXPEDICION><CERTIFICADO_CALIDAD>CERTIFICADO DE CALIDAD</CERTIFICADO_CALIDAD>
<FORMATO>1</FORMATO><TELEFONO_EXPEDICION>TEL: 33 3668-4500</TELEFONO_EXPEDICION>
<LIST_G_DATOS><G_DATOS>
<NUMERO_CERTIFICADO>CCA-123</NUMERO_CERTIFICADO><PRODUCTO>ALTA FRUCTOSA 55</PRODUCTO>
<FECHA_CERTIFICADO>02/07/2026</FECHA_CERTIFICADO><NUMERO_EMBARQUE>EMB-1</NUMERO_EMBARQUE>
<NOMBRE_CLIENTE>EMBOTELLADORA</NOMBRE_CLIENTE><PLANTA_PRODUCTORA>CEDAR RAPIDS, IA</PLANTA_PRODUCTORA>
<NOMBRE_INSPECTOR>Juan Perez</NOMBRE_INSPECTOR>
<LIST_G_VALORES>
<G_VALORES><CATEGORIA>ANALITICAS</CATEGORIA><CARACTERISTICA>FRUCTOSA %</CARACTERISTICA>
<VALOR>58.00</VALOR><MINIMO>55.00</MINIMO><MAXIMO>58.00</MAXIMO><USER_SEQUENCE>10</USER_SEQUENCE></G_VALORES>
<G_VALORES><CATEGORIA>ANALITICAS</CATEGORIA><CARACTERISTICA>FRUCTOSA %</CARACTERISTICA>
<VALOR>55.50</VALOR><MINIMO>55.00</MINIMO><MAXIMO>58.00</MAXIMO><RESULT_VALUE_NUM>55.5</RESULT_VALUE_NUM><USER_SEQUENCE>10</USER_SEQUENCE></G_VALORES>
<G_VALORES><CATEGORIA>SENSORIALES</CATEGORIA><CARACTERISTICA>COLOR</CARACTERISTICA>
<VALOR>INCOLORO</VALOR><USER_SEQUENCE>20</USER_SEQUENCE></G_VALORES>
</LIST_G_VALORES>
<LIST_G_SELLOS><G_SELLOS><SELLOS>111,222</SELLOS></G_SELLOS></LIST_G_SELLOS>
</G_DATOS></LIST_G_DATOS>
</G_DATOS_GENERALES></LIST_G_DATOS_GENERALES></DATA_DS>"""


def test_parse_header_fields():
    d = parse_certificate(SAMPLE_XML)
    assert d.formato == "1"
    assert d.cliente == "EMBOTELLADORA"
    assert d.inspector == "Juan Perez"
    assert d.planta_productora == "CEDAR RAPIDS, IA"
    assert d.sellos == "111,222"


def test_dedup_prefers_measured_value():
    d = parse_certificate(SAMPLE_XML)
    fructosa = [p for p in d.parametros if p.caracteristica == "FRUCTOSA %"]
    assert len(fructosa) == 1  # deduplicado
    assert fructosa[0].valor == "55.50"  # el medido, no el 58.00


def test_categoria_order():
    d = parse_certificate(SAMPLE_XML)
    titulos = [t for t, _ in d.parametros_por_categoria()]
    # Sensoriales antes que Analiticas segun el orden del PDF
    assert titulos.index("CARACTERISTICAS SENSORIALES") < titulos.index("ESPECIFICACIONES ANALITICAS")


def test_render_html_contains_data():
    d = parse_certificate(SAMPLE_XML)
    html = HtmlLayoutRenderer().render_html(d)
    assert "EMBOTELLADORA" in html
    assert "FRUCTOSA %" in html
    assert "55.50" in html
    assert "Juan Perez" in html
    assert "111,222" in html


def test_template_fallback_for_unknown_formato():
    d = parse_certificate(SAMPLE_XML)
    d.formato = "99"  # no existe formato99.html
    assert HtmlLayoutRenderer().template_name(d.formato) == "formato1.html"
