"""score_reconciler: compare a key/value dataset between two sources and report mismatches.

Columns can have any name, can differ between the two sources, and each source
may span several files (they are concatenated before comparison).
"""

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
