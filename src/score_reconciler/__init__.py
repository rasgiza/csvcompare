"""score_reconciler: compare Name/TotalScore data between two sources and report mismatches."""

from .loader import load_source, LoaderError
from .comparator import compare, ComparisonResult, Mismatch, RowDifference
from .reporter import build_report, write_report

__all__ = [
    "load_source",
    "LoaderError",
    "compare",
    "ComparisonResult",
    "Mismatch",
    "RowDifference",
    "build_report",
    "write_report",
]

__version__ = "0.1.0"
