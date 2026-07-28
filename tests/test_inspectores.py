import csv

from certificados.inspectores import (
    CSV_HEADER,
    create_default_csv,
    merge,
    parse_inspectores,
    read_csv,
    write_csv,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<DATA_DS>
<G_XXALM_INSPECTORES_CALIDAD><DESCRIPTION>Ricardo Campos</DESCRIPTION><LOOKUP_CODE>001</LOOKUP_CODE></G_XXALM_INSPECTORES_CALIDAD>
<G_XXALM_INSPECTORES_CALIDAD><DESCRIPTION>Hector Uriel Correa</DESCRIPTION><LOOKUP_CODE>003</LOOKUP_CODE></G_XXALM_INSPECTORES_CALIDAD>
<G_XXALM_INSPECTORES_CALIDAD><DESCRIPTION>Sergio Campos</DESCRIPTION><LOOKUP_CODE>002</LOOKUP_CODE></G_XXALM_INSPECTORES_CALIDAD>
</DATA_DS>"""


def test_parse_ordena_por_codigo_y_mapea_campos():
    filas = parse_inspectores(SAMPLE_XML)
    assert filas == [
        ("001", "Ricardo Campos"),
        ("002", "Sergio Campos"),
        ("003", "Hector Uriel Correa"),
    ]


def test_parse_ignora_filas_sin_codigo():
    xml = (
        "<DATA_DS><G_XXALM_INSPECTORES_CALIDAD><DESCRIPTION>Sin codigo</DESCRIPTION>"
        "<LOOKUP_CODE></LOOKUP_CODE></G_XXALM_INSPECTORES_CALIDAD></DATA_DS>"
    )
    assert parse_inspectores(xml) == []


def test_merge_agrega_nuevos():
    local = [("001", "Ricardo Campos")]
    remoto = [("001", "Ricardo Campos"), ("004", "Luis Daniel Rodriguez")]
    result = merge(local, remoto)
    assert result.nuevos == [("004", "Luis Daniel Rodriguez")]
    assert result.cambiados == []
    assert ("004", "Luis Daniel Rodriguez") in result.filas


def test_merge_reporte_gana_en_conflicto():
    local = [("074", "Oscar_Velasco_Pulido")]
    remoto = [("074", "Oscar Velasco Pulido")]
    result = merge(local, remoto)
    assert result.cambiados == [("074", "Oscar_Velasco_Pulido", "Oscar Velasco Pulido")]
    assert dict(result.filas)["074"] == "Oscar Velasco Pulido"


def test_merge_conserva_locales_ausentes_del_reporte():
    # Regla clave: nunca borrar inspectores que no vienen en el reporte.
    local = [("001", "Ricardo Campos"), ("999", "Inspector Manual")]
    remoto = [("001", "Ricardo Campos")]
    result = merge(local, remoto)
    assert result.conservados == [("999", "Inspector Manual")]
    assert dict(result.filas)["999"] == "Inspector Manual"
    assert result.total == 2


def test_merge_sin_cambios():
    filas = [("001", "Ricardo Campos")]
    result = merge(filas, filas)
    assert result.sin_cambios
    assert result.cambios == 0


def test_write_y_read_roundtrip_utf8(tmp_path):
    filas = [("001", "Ricardo Campos"), ("012", "Domingo Héctor Viveros Ortíz")]
    path = tmp_path / "inspector.csv"
    write_csv(path, filas)
    # Encabezado correcto y acentos preservados en UTF-8.
    text = path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == ",".join(CSV_HEADER)
    assert "Héctor" in text
    assert read_csv(path) == filas


def test_create_default_no_pisa_existente(tmp_path):
    path = tmp_path / "inspector.csv"
    write_csv(path, [("001", "Ricardo Campos")])
    creado = create_default_csv(path)  # overwrite=False
    assert creado is False
    assert read_csv(path) == [("001", "Ricardo Campos")]


def test_create_default_crea_encabezado_sin_datos(tmp_path):
    path = tmp_path / "inspector.csv"
    creado = create_default_csv(path)
    assert creado is True
    assert read_csv(path) == []
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows == [list(CSV_HEADER)]
