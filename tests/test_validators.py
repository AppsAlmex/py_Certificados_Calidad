from certificados.models import ReportRequest
from certificados.validators import (
    ChoiceRule,
    DateRule,
    NumericRule,
    RequiredFieldRule,
    RequestValidator,
    build_default_validator,
)


def make(**params):
    base = {"P_EMBARQUE": "1", "P_FORMATO": "1", "P_INSPECTOR": "3",
            "P_PLANTA_PROD": "P", "P_TANQUE": "T"}
    base.update(params)
    fmt = base.pop("_format", "pdf")
    return ReportRequest(row_number=2, params=base, output_format=fmt)


def test_valid_request_passes():
    result = build_default_validator().validate(make(P_CANTIDAD1="2"))
    assert result.valid
    assert result.issues == []


def test_required_field_missing():
    result = build_default_validator().validate(make(P_EMBARQUE=""))
    assert not result.valid
    assert any(i.field == "P_EMBARQUE" for i in result.issues)
    assert result.issues[0].row == 2


def test_tanque_es_opcional():
    # P_TANQUE ya no es requerido: vacio o ausente debe pasar.
    assert build_default_validator().validate(make(P_TANQUE="")).valid
    sin_tanque = build_default_validator().validate(
        ReportRequest(2, {"P_EMBARQUE": "1", "P_FORMATO": "1", "P_INSPECTOR": "3",
                          "P_PLANTA_PROD": "P"}, output_format="pdf"))
    assert sin_tanque.valid


def test_bad_output_format():
    result = build_default_validator().validate(make(_format="docx"))
    assert not result.valid
    assert any("FORMATO_SALIDA" == i.field for i in result.issues)


def test_non_numeric_quantity():
    result = build_default_validator().validate(make(P_CANTIDAD1="abc"))
    assert not result.valid
    assert any(i.field == "P_CANTIDAD1" for i in result.issues)


def test_numeric_allows_empty():
    rule = NumericRule("P_CANTIDAD1", allow_empty=True)
    assert rule.validate(make(P_CANTIDAD1="")) == []


def test_choice_case_insensitive():
    rule = ChoiceRule("FORMATO_SALIDA", ["pdf", "xlsx"])
    assert rule.validate(make(_format="PDF")) == []


def test_date_rule():
    rule = DateRule("FECHA")
    ok = ReportRequest(2, {"FECHA": "2026-01-01"})
    bad = ReportRequest(3, {"FECHA": "01/01/2026"})
    assert rule.validate(ok) == []
    assert len(rule.validate(bad)) == 1


def test_add_rule_extends_without_modifying():
    validator = RequestValidator([RequiredFieldRule("P_EMBARQUE")])
    validator.add_rule(RequiredFieldRule("P_TANQUE"))
    result = validator.validate(ReportRequest(2, {"P_EMBARQUE": "1", "P_TANQUE": ""}))
    assert not result.valid
