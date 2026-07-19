"""File loading utilities.

Reads a CSV or Excel file and extracts only the columns we care about
(``Name`` and ``TotalScore``). Column matching is case-insensitive and
tolerant of surrounding whitespace so that "total score", "TotalScore",
and "TOTALSCORE " all resolve correctly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

NAME_COLUMN = "Name"
SCORE_COLUMN = "TotalScore"

# Accepted header aliases (normalized to lowercase, no spaces).
_NAME_ALIASES = {"name", "fullname", "candidatename"}
_SCORE_ALIASES = {"totalscore", "score", "total"}

_CSV_SUFFIXES = {".csv"}
_EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm"}


class LoaderError(Exception):
    """Raised when a source file cannot be read or is missing required columns."""


def _normalize(header: str) -> str:
    return "".join(str(header).lower().split())


def _resolve_column(columns: Iterable[str], aliases: set[str], friendly: str) -> str:
    for col in columns:
        if _normalize(col) in aliases:
            return col
    raise LoaderError(
        f"Could not find a '{friendly}' column. "
        f"Available columns: {list(columns)}"
    )


def _read_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in _CSV_SUFFIXES:
        return pd.read_csv(path)
    if suffix in _EXCEL_SUFFIXES:
        return pd.read_excel(path)
    raise LoaderError(
        f"Unsupported file type '{suffix}' for {path.name}. "
        f"Supported: {sorted(_CSV_SUFFIXES | _EXCEL_SUFFIXES)}"
    )


def load_source(path: str | Path) -> pd.DataFrame:
    """Load a source file and return a normalized DataFrame.

    The returned frame has exactly two columns: ``Name`` (str, trimmed) and
    ``TotalScore`` (numeric). Rows with a blank name are dropped.
    """
    path = Path(path)
    if not path.exists():
        raise LoaderError(f"File not found: {path}")

    raw = _read_frame(path)
    if raw.empty:
        raise LoaderError(f"File is empty: {path.name}")

    name_col = _resolve_column(raw.columns, _NAME_ALIASES, NAME_COLUMN)
    score_col = _resolve_column(raw.columns, _SCORE_ALIASES, SCORE_COLUMN)

    frame = raw[[name_col, score_col]].copy()
    frame.columns = [NAME_COLUMN, SCORE_COLUMN]

    frame[NAME_COLUMN] = frame[NAME_COLUMN].astype(str).str.strip()
    frame[SCORE_COLUMN] = pd.to_numeric(frame[SCORE_COLUMN], errors="coerce")

    frame = frame[frame[NAME_COLUMN] != ""]
    frame = frame[frame[NAME_COLUMN].str.lower() != "nan"]

    return frame.reset_index(drop=True)
