import pytest

from certificados.csv_reader import CSVReader
from certificados.exceptions import CSVReadError

HEADER = (
    "embarque,formato,inspector,observaciones,planta_prod,tanque,"
    "sello1,cantidad1,sello2,cantidad2,sello3,cantidad3,sello4,cantidad4,"
    "formato_salida,nombre_archivo\n"
)


def write_csv(tmp_path, body, header=HEADER):
    path = tmp_path / "data.csv"
    path.write_text(header + body, encoding="utf-8")
    return path


def test_reads_rows_into_requests(tmp_path):
    path = write_csv(tmp_path, '256436,1,003,,PLANT,TANK,951,2,,,,,,,pdf,\n')
    requests = CSVReader(path).read()
    assert len(requests) == 1
    req = requests[0]
    assert req.row_number == 2
    assert req.params["P_EMBARQUE"] == "256436"
    assert req.output_format == "pdf"
    assert req.output_name is None


def test_default_format_is_pdf_when_blank(tmp_path):
    path = write_csv(tmp_path, "256436,1,003,,PLANT,TANK,951,2,,,,,,,,\n")
    req = CSVReader(path).read()[0]
    assert req.output_format == "pdf"


def test_missing_file_raises(tmp_path):
    with pytest.raises(CSVReadError, match="no encontrado"):
        CSVReader(tmp_path / "nope.csv").read()


def test_missing_column_raises(tmp_path):
    path = write_csv(tmp_path, "x\n", header="embarque\n")
    with pytest.raises(CSVReadError, match="Faltan columnas"):
        CSVReader(path).read()


def test_empty_data_raises(tmp_path):
    path = write_csv(tmp_path, "")
    with pytest.raises(CSVReadError, match="no contiene filas"):
        CSVReader(path).read()


def test_explicit_output_name_kept(tmp_path):
    path = write_csv(tmp_path, "256436,1,003,,PLANT,TANK,951,2,,,,,,,pdf,MiArchivo\n")
    req = CSVReader(path).read()[0]
    assert req.output_name == "MiArchivo"
    assert req.resolved_name() == "MiArchivo.pdf"
