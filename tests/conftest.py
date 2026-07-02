import base64
from pathlib import Path

import pytest

from certificados.config import Settings
from certificados.models import ReportRequest


@pytest.fixture(autouse=True)
def _clean_cert_env(monkeypatch):
    """Isolate tests: load_dotenv no sobrescribe os.environ, asi que limpiamos
    las variables CERT_* antes de cada test para que el .env de cada caso mande."""
    for var in ("CERT_USER", "CERT_PASSWORD", "CERT_TIMEOUT", "CERT_REPORT"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        host="https://example.test",
        service_path="/xmlpserver/services/v2/ReportService",
        report_path="/Custom/Report.xdo",
        report_key="certificado_calidad",
        reports={"certificado_calidad": "/Custom/Report.xdo"},
        user="user",
        password="pass",
        timeout=30,
        verify_ssl=False,
        output_dir=tmp_path / "output",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )


@pytest.fixture
def valid_request() -> ReportRequest:
    return ReportRequest(
        row_number=2,
        params={
            "P_EMBARQUE": "256436",
            "P_FORMATO": "1",
            "P_INSPECTOR": "003",
            "P_OBSERVACIONES": "",
            "P_PLANTA_PROD": "MARSHALL, MN",
            "P_TANQUE": "ADMX0106215",
            "P_SELLO1": "951",
            "P_CANTIDAD1": "2",
        },
        output_format="pdf",
    )


class FakeResponse:
    def __init__(self, status_code=200, content=b"", headers=None, text=""):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {"Content-Type": "text/xml"}
        self.text = text


def soap_response(report_bytes: bytes) -> bytes:
    encoded = base64.b64encode(report_bytes).decode()
    return (
        f'<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">'
        f"<env:Body><runReportResponse><runReportReturn>"
        f"<reportBytes>{encoded}</reportBytes>"
        f"</runReportReturn></runReportResponse></env:Body></env:Envelope>"
    ).encode()


@pytest.fixture
def fake_response_factory():
    return FakeResponse
