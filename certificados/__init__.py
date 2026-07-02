"""Bulk report execution package for Oracle BI Publisher (Certificados de Calidad).

Public API re-exported for convenience.
"""
from .config import Settings, load_settings
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
)
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
from .executor import ReportGateway, OracleReportClient
from .result_logger import ResultLogger
from .batch import BatchProcessor, ConcurrentBatchProcessor

__all__ = [
    "Settings",
    "load_settings",
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
    "ResultLogger",
    "BatchProcessor",
    "ConcurrentBatchProcessor",
]
