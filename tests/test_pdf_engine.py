import dataclasses

from certificados.executor import LocalPdfReportGateway, OracleReportClient, build_gateway
from certificados.models import ReportRequest, ReportResult

SAMPLE_XML = b"""<?xml version="1.0"?><DATA_DS><P_FORMATO>1</P_FORMATO>
<LIST_G_DATOS_GENERALES><G_DATOS_GENERALES><FORMATO>1</FORMATO>
<LIST_G_DATOS><G_DATOS><NOMBRE_CLIENTE>ACME</NOMBRE_CLIENTE>
<LIST_G_VALORES></LIST_G_VALORES></G_DATOS></LIST_G_DATOS>
</G_DATOS_GENERALES></LIST_G_DATOS_GENERALES></DATA_DS>"""


def test_build_gateway_oracle(settings):
    assert isinstance(build_gateway(settings), OracleReportClient)


def test_build_gateway_local(settings):
    local = dataclasses.replace(settings, pdf_engine="local")
    assert isinstance(build_gateway(local), LocalPdfReportGateway)


class FakeOracle:
    def __init__(self):
        self.fetched = None
        self.delegated = None

    def fetch_bytes(self, request):
        self.fetched = request
        return SAMPLE_XML

    def run_report(self, request):
        self.delegated = request
        from pathlib import Path
        return ReportResult(request, Path("oracle.xlsx"), 1)


class FakeRenderer:
    def render(self, data):
        return b"%PDF-fake " + data.cliente.encode()


def test_local_pdf_renders_from_xml(settings):
    oracle = FakeOracle()
    gw = LocalPdfReportGateway(settings, oracle_client=oracle, renderer=FakeRenderer())
    req = ReportRequest(1, {"P_EMBARQUE": "100"}, output_format="pdf")
    result = gw.run_report(req)
    # pidio XML a Oracle (no pdf) y renderizo local
    assert oracle.fetched.output_format == "xml"
    assert result.file_path.exists()
    content = result.file_path.read_bytes()
    assert content.startswith(b"%PDF-fake")
    assert b"ACME" in content


def test_local_pdf_delegates_non_pdf(settings):
    oracle = FakeOracle()
    gw = LocalPdfReportGateway(settings, oracle_client=oracle, renderer=FakeRenderer())
    req = ReportRequest(1, {"P_EMBARQUE": "100"}, output_format="xlsx")
    gw.run_report(req)
    # xlsx no tiene layout local -> delega en Oracle tal cual
    assert oracle.delegated is req
    assert oracle.fetched is None
