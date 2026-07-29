"""Bulk report execution package for Oracle BI Publisher (Certificados de Calidad).

Public API re-exported for convenience.
"""
__version__ = "1.2.3"

from .config import MAX_WORKERS, MIN_WORKERS, Settings, load_settings, save_config
from .catalogs import CatalogEntry, load_catalog, parse_valor, validate_catalog
from .health import HealthResult, run_health_checks
from .logs import LogRun, list_runs, read_log_text, read_results
from .log_share import build_share_zip
from .models import ReportRequest, ReportResult, BatchSummary
from .exceptions import (
    CertificadoError,
    ConfigError,
    CSVReadError,
    ValidationFailedError,
    AuthenticationError,
    ReportConnectionError,
    ReportGenerationError,
    FileSaveError,
    LayoutError,
)
from .pdf_renderer import available_local_formats
from .labels import LabelData, render_label_html, render_label_pdf
from .csv_reader import CSVReader
from .validators import (
    RequestValidator,
    ValidationRule,
    ValidationIssue,
    ValidationResult,
    RequiredFieldRule,
    ChoiceRule,
    NumericRule,
    DateRule,
    build_default_validator,
)
from .executor import ReportGateway, OracleReportClient, LocalPdfReportGateway, build_gateway
from .diagnostics import (
    InMemoryTransportCapture,
    NullTransportCapture,
    TransportCapture,
    TransportRecord,
    expand_params,
    redact_soap,
)
from .result_logger import ResultLogger
from .batch import BatchProcessor, ConcurrentBatchProcessor, execute_and_log

__all__ = [
    "Settings",
    "load_settings",
    "save_config",
    "MAX_WORKERS",
    "MIN_WORKERS",
    "CatalogEntry",
    "load_catalog",
    "parse_valor",
    "validate_catalog",
    "HealthResult",
    "run_health_checks",
    "LogRun",
    "list_runs",
    "read_log_text",
    "read_results",
    "build_share_zip",
    "ReportRequest",
    "ReportResult",
    "BatchSummary",
    "CertificadoError",
    "ConfigError",
    "CSVReadError",
    "ValidationFailedError",
    "AuthenticationError",
    "ReportConnectionError",
    "ReportGenerationError",
    "FileSaveError",
    "CSVReader",
    "RequestValidator",
    "ValidationRule",
    "ValidationIssue",
    "ValidationResult",
    "RequiredFieldRule",
    "ChoiceRule",
    "NumericRule",
    "DateRule",
    "build_default_validator",
    "ReportGateway",
    "OracleReportClient",
    "LocalPdfReportGateway",
    "build_gateway",
    "available_local_formats",
    "LabelData",
    "render_label_html",
    "render_label_pdf",
    "LayoutError",
    "ResultLogger",
    "TransportCapture",
    "TransportRecord",
    "NullTransportCapture",
    "InMemoryTransportCapture",
    "expand_params",
    "redact_soap",
    "BatchProcessor",
    "ConcurrentBatchProcessor",
    "execute_and_log",
]
