"""score_reconciler: compare a key/value dataset between two sources and report mismatches.

Columns can have any name, can differ between the two sources, and each source
may span several files (they are concatenated before comparison).
"""

from .loader import load_source, load_mapped, LoaderError
from .comparator import (
    compare,
    compare_mapped,
    ComparisonResult,
    MappedResult,
    Mismatch,
    CellMismatch,
    CellComparison,
    RowDifference,
)
from .mapping import Mapping, MappingError, ColumnMap
from .reporter import build_report, build_mapped_report, write_report

__all__ = [
    "load_source",
    "load_mapped",
    "LoaderError",
    "compare",
    "compare_mapped",
    "ComparisonResult",
    "MappedResult",
    "Mismatch",
    "CellMismatch",
    "CellComparison",
    "RowDifference",
    "Mapping",
    "MappingError",
    "ColumnMap",
    "build_report",
    "build_mapped_report",
    "write_report",
]

__version__ = "0.1.0"
