import pytest
import requests

from certificados.exceptions import (
    AuthenticationError,
    FileSaveError,
    ReportConnectionError,
    ReportGenerationError,
)
from certificados.executor import OracleReportClient
from tests.conftest import FakeResponse, soap_response


class FakeSession:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.last_call = None

    def post(self, url, **kwargs):
        self.last_call = (url, kwargs)
        if self._exc:
            raise self._exc
        return self._response


def test_run_report_saves_file(settings, valid_request):
    session = FakeSession(FakeResponse(content=soap_response(b"%PDF-1.4 fake")))
    client = OracleReportClient(settings, session=session)
    result = client.run_report(valid_request)
    assert result.file_path.exists()
    assert result.file_path.read_bytes() == b"%PDF-1.4 fake"
    assert result.size_bytes == len(b"%PDF-1.4 fake")


def test_soap_body_contains_params_and_creds(settings, valid_request):
    session = FakeSession(FakeResponse(content=soap_response(b"x")))
    OracleReportClient(settings, session=session).run_report(valid_request)
    body = session.last_call[1]["data"].decode()
    assert "P_EMBARQUE" in body
    assert "256436" in body
    assert "<v2:userID>user</v2:userID>" in body


def test_http_401_is_auth_error(settings, valid_request):
    session = FakeSession(FakeResponse(status_code=401, text="nope"))
    with pytest.raises(AuthenticationError):
        OracleReportClient(settings, session=session).run_report(valid_request)


def test_http_500_is_generation_error(settings, valid_request):
    session = FakeSession(FakeResponse(status_code=500, text="boom"))
    with pytest.raises(ReportGenerationError):
        OracleReportClient(settings, session=session).run_report(valid_request)


def test_timeout_is_connection_error(settings, valid_request):
    session = FakeSession(exc=requests.exceptions.Timeout())
    with pytest.raises(ReportConnectionError):
        OracleReportClient(settings, session=session).run_report(valid_request)


def test_missing_report_bytes(settings, valid_request):
    session = FakeSession(FakeResponse(content=b"<a><b>no bytes</b></a>"))
    with pytest.raises(ReportGenerationError, match="reportBytes"):
        OracleReportClient(settings, session=session).run_report(valid_request)


def test_non_xml_response(settings, valid_request):
    session = FakeSession(FakeResponse(content=b"<html>", headers={"Content-Type": "text/html"}))
    with pytest.raises(ReportGenerationError, match="no XML"):
        OracleReportClient(settings, session=session).run_report(valid_request)


def test_soap_fault_auth(settings, valid_request):
    fault = b'<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/"><env:Body><env:Fault><faultstring>Invalid credential</faultstring></env:Fault></env:Body></env:Envelope>'
    session = FakeSession(FakeResponse(content=fault))
    with pytest.raises(AuthenticationError):
        OracleReportClient(settings, session=session).run_report(valid_request)


def test_save_error(settings, valid_request, monkeypatch):
    session = FakeSession(FakeResponse(content=soap_response(b"x")))
    client = OracleReportClient(settings, session=session)

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr("pathlib.Path.write_bytes", boom)
    with pytest.raises(FileSaveError):
        client.run_report(valid_request)
