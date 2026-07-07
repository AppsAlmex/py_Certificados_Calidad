import pytest

from certificados.catalogs import CatalogEntry, load_catalog, parse_valor, validate_catalog
from certificados.exceptions import CatalogError


def write(tmp_path, text, name="cat.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_load_catalog_valor_descripcion(tmp_path):
    path = write(tmp_path, "valor,descripcion\n1,Estandar\n2,Exportacion\n")
    entries = load_catalog(path)
    assert entries == [CatalogEntry("1", "Estandar"), CatalogEntry("2", "Exportacion")]
    assert entries[0].display == "1 - Estandar"


def test_load_catalog_only_valor(tmp_path):
    path = write(tmp_path, "valor\nA\nB\n")
    entries = load_catalog(path)
    assert [e.valor for e in entries] == ["A", "B"]
    assert entries[0].display == "A"  # sin descripcion


def test_load_catalog_quoted_value_with_comma(tmp_path):
    path = write(tmp_path, 'valor,descripcion\n"MARSHALL, MN",Planta\n')
    entries = load_catalog(path)
    assert entries[0].valor == "MARSHALL, MN"


def test_missing_file_returns_empty(tmp_path):
    assert load_catalog(tmp_path / "nope.csv") == []


def test_missing_valor_column_raises(tmp_path):
    path = write(tmp_path, "codigo,descripcion\n1,x\n")
    with pytest.raises(CatalogError, match="valor"):
        load_catalog(path)


def test_blank_rows_ignored(tmp_path):
    path = write(tmp_path, "valor,descripcion\n1,Uno\n,\n2,Dos\n")
    assert [e.valor for e in load_catalog(path)] == ["1", "2"]


@pytest.mark.parametrize("text,expected", [
    ("1 - Estandar", "1"),
    ("003 - Inspector 003", "003"),
    ("MARSHALL, MN", "MARSHALL, MN"),
    ("", ""),
    ("  5  ", "5"),
])
def test_parse_valor(text, expected):
    assert parse_valor(text) == expected


def test_validate_catalog_ok(tmp_path):
    path = write(tmp_path, "valor,descripcion\n1,Uno\n2,Dos\n")
    assert validate_catalog(path) == []


def test_validate_catalog_missing_file(tmp_path):
    assert validate_catalog(tmp_path / "no.csv") == ["no.csv: no existe"]


def test_validate_catalog_no_valor_column(tmp_path):
    path = write(tmp_path, "codigo,descripcion\n1,x\n")
    assert any("valor" in m for m in validate_catalog(path))


def test_validate_catalog_duplicates_and_empty(tmp_path):
    path = write(tmp_path, "valor,descripcion\n1,A\n1,B\n,C\n")
    issues = validate_catalog(path)
    assert any("duplicado" in m for m in issues)
    assert any("vacio" in m for m in issues)
