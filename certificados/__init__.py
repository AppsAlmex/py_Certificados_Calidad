"""Bulk report execution package for Oracle BI Publisher (Certificados de Calidad).

Public API re-exported for convenience.
"""
from .config import MAX_WORKERS, MIN_WORKERS, Settings, load_settings, save_config
from .catalogs import CatalogEntry, load_catalog, parse_valor
from .logs import LogRun, list_runs, read_log_text, read_results
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
    "LogRun",
    "list_runs",
    "read_log_text",
    "read_results",
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
    "LayoutError",
    "ResultLogger",
    "BatchProcessor",
    "ConcurrentBatchProcessor",
    "execute_and_log",
]
