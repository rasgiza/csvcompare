"""File loading utilities.

Reads one or more CSV/Excel files and extracts two columns: a **key** column
(used to match rows between the two sources) and a **value** column (the number
that is compared).

Flexibility:
- The key/value columns can have **any** header. If you don't say which columns
  to use, common names are auto-detected (``Name`` and ``TotalScore`` plus a few
  aliases).
- The two sources can use **different** header names for the same data (e.g.
  Source A calls the key ``Candidate`` while Source B calls it ``Student``);
  just pass the right column name for each source.
- A single source can be **several files**; they are concatenated (stacked)
  before comparison, so 6-7 CSVs on one side is fine.

Column matching is case-insensitive and tolerant of surrounding whitespace so
``total score``, ``TotalScore`` and ``TOTALSCORE `` all resolve to the same
column.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable

import pandas as pd

# Internal canonical column names used everywhere downstream.
NAME_COLUMN = "Name"
SCORE_COLUMN = "TotalScore"

# Auto-detect aliases used only when the caller does not name the columns.
_NAME_ALIASES = {"name", "fullname", "candidatename", "candidate", "student", "id"}
_SCORE_ALIASES = {"totalscore", "score", "total", "points", "amount", "value"}

_CSV_SUFFIXES = {".csv", ".tsv", ".txt"}
_EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm"}


class LoaderError(Exception):
    """Raised when a source file cannot be read or is missing required columns."""


def _normalize(header: str) -> str:
    return "".join(str(header).lower().split())


# Invisible characters that make two otherwise-identical keys compare unequal:
# zero-width space/non-joiner/joiner/word-joiner and the BOM.
_INVISIBLE_CHARS = dict.fromkeys(
    [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF], None
)
_WHITESPACE_RUN = re.compile(r"\s+")


def _clean_key(value: object) -> str:
    """Aggressively normalize a key value so grouping/summing is reliable.

    Removes the "hidden" differences that silently split a group:
    - Unicode compatibility normalization (NFKC) folds full-width, ligature and
      look-alike forms to a canonical form.
    - Zero-width and BOM characters are stripped.
    - Remaining control / non-printing characters (Unicode category ``C*``) are
      removed.
    - Every run of whitespace (spaces, tabs, non-breaking spaces, newlines) is
      collapsed to a single regular space, then the ends are trimmed.

    Casing is preserved so the report still shows the original spelling.
    """
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.translate(_INVISIBLE_CHARS)
    text = "".join(ch for ch in text if not unicodedata.category(ch).startswith("C"))
    text = _WHITESPACE_RUN.sub(" ", text)
    return text.strip()


def _to_numeric(series: pd.Series) -> pd.Series:
    """Coerce a column to numbers, tolerating thousands separators.

    Values like ``"55,000.00"`` (comma thousands separator, often produced when
    a numeric export is quoted) would otherwise become ``NaN`` under pandas'
    strict parser and silently drop out of a ``sum`` - leaving only the rows
    that happened to be comma-free and making the total look like a single
    detail row. Commas and surrounding whitespace are stripped before
    conversion; anything still non-numeric becomes ``NaN``.
    """
    cleaned = series.astype(str).str.strip().str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def _resolve_column(
    columns: Iterable[str],
    explicit: str | None,
    aliases: set[str],
    friendly: str,
    file_name: str,
) -> str:
    """Find the source column to use.

    If ``explicit`` is given, match that exact header (case/space-insensitive).
    Otherwise fall back to the known ``aliases``.
    """
    columns = list(columns)
    if explicit:
        target = _normalize(explicit)
        for col in columns:
            if _normalize(col) == target:
                return col
        raise LoaderError(
            f"Column '{explicit}' not found in {file_name}. "
            f"Available columns: {columns}"
        )

    for col in columns:
        if _normalize(col) in aliases:
            return col
    raise LoaderError(
        f"Could not auto-detect a '{friendly}' column in {file_name}. "
        f"Specify it explicitly (e.g. --key / --value). Available columns: {columns}"
    )


def _read_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in _CSV_SUFFIXES:
        sep = "\t" if suffix == ".tsv" else None
        return pd.read_csv(path, sep=sep, engine="python")
    if suffix in _EXCEL_SUFFIXES:
        return pd.read_excel(path)
    raise LoaderError(
        f"Unsupported file type '{suffix}' for {path.name}. "
        f"Supported: {sorted(_CSV_SUFFIXES | _EXCEL_SUFFIXES)}"
    )


def _load_one(path: Path, key: str | None, value: str | None) -> pd.DataFrame:
    if not path.exists():
        raise LoaderError(f"File not found: {path}")

    raw = _read_frame(path)
    if raw.empty:
        raise LoaderError(f"File is empty: {path.name}")

    key_col = _resolve_column(raw.columns, key, _NAME_ALIASES, "key/name", path.name)
    value_col = _resolve_column(raw.columns, value, _SCORE_ALIASES, "value/score", path.name)

    frame = raw[[key_col, value_col]].copy()
    frame.columns = [NAME_COLUMN, SCORE_COLUMN]

    frame[NAME_COLUMN] = frame[NAME_COLUMN].map(_clean_key)
    frame[SCORE_COLUMN] = _to_numeric(frame[SCORE_COLUMN])

    frame = frame[frame[NAME_COLUMN] != ""]
    frame = frame[frame[NAME_COLUMN].str.lower() != "nan"]

    return frame.reset_index(drop=True)


def load_source(
    paths: str | Path | Iterable[str | Path],
    key: str | None = None,
    value: str | None = None,
) -> pd.DataFrame:
    """Load one or more source files into a single normalized DataFrame.

    Args:
        paths: A single file path, or an iterable of paths. Multiple files are
            stacked (concatenated) into one source.
        key: Header of the column to match rows on. If ``None``, it is
            auto-detected from common aliases.
        value: Header of the numeric column to compare. If ``None``, it is
            auto-detected from common aliases.

    Returns:
        DataFrame with exactly two columns: ``Name`` (the key, as trimmed text)
        and ``TotalScore`` (the value, coerced to numeric). Rows with a blank
        key are dropped.
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]
    path_list = [Path(p) for p in paths]
    if not path_list:
        raise LoaderError("No source files were provided.")

    frames = [_load_one(p, key, value) for p in path_list]
    combined = pd.concat(frames, ignore_index=True)
    if combined.empty:
        names = ", ".join(p.name for p in path_list)
        raise LoaderError(f"No usable rows found in: {names}")
    return combined


# Canonical key column name used by the mapped (multi-column) path.
KEY_COLUMN = "__key__"


def _load_one_mapped(path: Path, key_col_name: str, columns, side: str) -> "pd.DataFrame":
    """Load one file for the mapped path: key + every mapped column for ``side``.

    ``columns`` is a list of ``mapping.ColumnMap``. ``side`` is ``"a"`` or
    ``"b"`` and selects which source header / unit each column uses. Values are
    coerced to numeric and unit-converted to the column's ``to_unit``.
    """
    if not path.exists():
        raise LoaderError(f"File not found: {path}")

    raw = _read_frame(path)
    if raw.empty:
        raise LoaderError(f"File is empty: {path.name}")

    key_col = _resolve_column(raw.columns, key_col_name, set(), "key", path.name)
    data = {KEY_COLUMN: raw[key_col].map(_clean_key)}

    for col in columns:
        header = col.source_a if side == "a" else col.source_b
        multiplier = col.multiplier_a() if side == "a" else col.multiplier_b()
        source_col = _resolve_column(raw.columns, header, set(), col.name, path.name)
        values = _to_numeric(raw[source_col])
        data[col.name] = values * multiplier

    frame = pd.DataFrame(data)
    frame = frame[frame[KEY_COLUMN] != ""]
    frame = frame[frame[KEY_COLUMN].str.lower() != "nan"]
    return frame.reset_index(drop=True)


def load_mapped(
    paths: str | Path | Iterable[str | Path],
    mapping,
    side: str,
) -> "pd.DataFrame":
    """Load one or more files for a mapped (multi-column) comparison.

    Args:
        paths: A single path or an iterable of paths (stacked together).
        mapping: A ``mapping.Mapping`` describing the key, columns, and units.
        side: ``"a"`` or ``"b"`` - which source's headers/units to read.

    Returns:
        DataFrame with a canonical key column plus one column per mapped metric
        (named ``ColumnMap.name``), numeric and unit-converted.
    """
    if side not in ("a", "b"):
        raise LoaderError("side must be 'a' or 'b'.")
    key_col_name = mapping.key_a if side == "a" else mapping.key_b

    if isinstance(paths, (str, Path)):
        paths = [paths]
    path_list = [Path(p) for p in paths]
    if not path_list:
        raise LoaderError("No source files were provided.")

    frames = [
        _load_one_mapped(p, key_col_name, mapping.columns, side) for p in path_list
    ]
    combined = pd.concat(frames, ignore_index=True)
    if combined.empty:
        names = ", ".join(p.name for p in path_list)
        raise LoaderError(f"No usable rows found in: {names}")
    return combined
