"""Comparison logic between Source A and Source B.

We match rows by ``Name`` and compare ``TotalScore``. The score difference
must be exactly 0 to count as a match; any non-zero absolute difference is a
mismatch. Names that exist in only one source are reported separately so QA
can investigate row-count differences (e.g. caused by different date ranges).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .loader import KEY_COLUMN, NAME_COLUMN, SCORE_COLUMN


@dataclass
class Mismatch:
    """A name present in both sources whose scores differ."""

    name: str
    score_a: float
    score_b: float

    @property
    def difference(self) -> float:
        return self.score_a - self.score_b

    @property
    def abs_difference(self) -> float:
        return abs(self.difference)


@dataclass
class RowDifference:
    """A name that appears in one source but not the other."""

    name: str
    present_in: str  # "A" or "B"
    score: float


@dataclass
class ComparisonResult:
    total_a: int
    total_b: int
    matched: int
    mismatches: list[Mismatch] = field(default_factory=list)
    only_in_a: list[RowDifference] = field(default_factory=list)
    only_in_b: list[RowDifference] = field(default_factory=list)
    strategy: str = "last"
    unique_a: int = 0
    unique_b: int = 0
    duplicates_a: int = 0
    duplicates_b: int = 0

    @property
    def has_issues(self) -> bool:
        return bool(self.mismatches or self.only_in_a or self.only_in_b)

    @property
    def row_count_matches(self) -> bool:
        return self.total_a == self.total_b


# Supported ways to collapse multiple rows that share the same name.
DUPLICATE_STRATEGIES = ("sum", "mean", "last", "first", "max", "min")


def _aggregate(frame: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Pivot rows down to one row per name using the chosen strategy.

    When the same name appears on several rows, this collapses them into a
    single value so the comparison is stable regardless of spreadsheet shape.
    ``sum`` totals the scores; ``last``/``first`` keep a single occurrence.
    """
    if strategy not in DUPLICATE_STRATEGIES:
        raise ValueError(
            f"Unknown duplicate strategy '{strategy}'. "
            f"Choose one of: {', '.join(DUPLICATE_STRATEGIES)}"
        )

    grouped = frame.groupby(NAME_COLUMN, sort=False, as_index=False)
    if strategy in ("last", "first"):
        aggregated = getattr(grouped, strategy)()
    else:
        aggregated = grouped.agg({SCORE_COLUMN: strategy})
    return aggregated


def compare(
    source_a: pd.DataFrame,
    source_b: pd.DataFrame,
    tolerance: float = 0.0,
    duplicate_strategy: str = "last",
) -> ComparisonResult:
    """Compare two normalized source frames.

    Args:
        source_a: Normalized frame from Source A.
        source_b: Normalized frame from Source B.
        tolerance: Allowed absolute score difference. Default 0.0 means any
            non-zero difference is flagged.
        duplicate_strategy: How to collapse rows that share the same name
            before comparing (``last`` by default: keep one row per name and
            take the score difference). Use ``sum`` to total scores per name.
            See ``DUPLICATE_STRATEGIES``.
    """
    agg_a = _aggregate(source_a, duplicate_strategy)
    agg_b = _aggregate(source_b, duplicate_strategy)

    a = agg_a.set_index(NAME_COLUMN)
    b = agg_b.set_index(NAME_COLUMN)

    names_a = set(a.index)
    names_b = set(b.index)

    result = ComparisonResult(
        total_a=len(source_a),
        total_b=len(source_b),
        matched=0,
        strategy=duplicate_strategy,
        unique_a=len(agg_a),
        unique_b=len(agg_b),
        duplicates_a=len(source_a) - len(agg_a),
        duplicates_b=len(source_b) - len(agg_b),
    )

    # Names only in A (Source A often has more rows than B).
    for name in sorted(names_a - names_b):
        result.only_in_a.append(
            RowDifference(name=name, present_in="A", score=float(a.loc[name, SCORE_COLUMN]))
        )

    # Names only in B.
    for name in sorted(names_b - names_a):
        result.only_in_b.append(
            RowDifference(name=name, present_in="B", score=float(b.loc[name, SCORE_COLUMN]))
        )

    # Names in both: compare scores.
    for name in sorted(names_a & names_b):
        score_a = float(a.loc[name, SCORE_COLUMN])
        score_b = float(b.loc[name, SCORE_COLUMN])
        if abs(score_a - score_b) > tolerance:
            result.mismatches.append(
                Mismatch(name=name, score_a=score_a, score_b=score_b)
            )
        else:
            result.matched += 1

    return result


# ---------------------------------------------------------------------------
# Mapped (multi-column) comparison
# ---------------------------------------------------------------------------


@dataclass
class CellMismatch:
    """A single mapped column whose value differs for a matched key."""

    key: str
    column: str
    value_a: float
    value_b: float

    @property
    def difference(self) -> float:
        return self.value_a - self.value_b

    @property
    def abs_difference(self) -> float:
        return abs(self.difference)


@dataclass
class MappedResult:
    total_a: int
    total_b: int
    unique_a: int
    unique_b: int
    duplicates_a: int
    duplicates_b: int
    columns: list[str]
    aggregate: str
    matched_keys: int = 0
    mismatches: list[CellMismatch] = field(default_factory=list)
    only_in_a: list[str] = field(default_factory=list)
    only_in_b: list[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.mismatches or self.only_in_a or self.only_in_b)

    @property
    def row_count_matches(self) -> bool:
        return self.total_a == self.total_b


def _aggregate_mapped(frame: pd.DataFrame, columns: list[str], strategy: str) -> pd.DataFrame:
    """Collapse rows to one per key, aggregating every mapped column.

    This is the "pivot": several rows sharing a key (e.g. three Kibana rows for
    ``desm001``) become a single row so they line up with the one row in the
    other source. ``sum`` totals each column; ``last``/``first`` keep one row.
    """
    grouped = frame.groupby(KEY_COLUMN, sort=False, as_index=False)
    if strategy in ("last", "first"):
        return getattr(grouped, strategy)()
    if strategy == "count":
        return grouped.agg({c: "count" for c in columns})
    return grouped.agg({c: strategy for c in columns})


def compare_mapped(
    source_a: pd.DataFrame,
    source_b: pd.DataFrame,
    mapping,
) -> MappedResult:
    """Compare two frames produced by ``loader.load_mapped`` using a mapping.

    Rows are matched on the canonical key column, each source is pivoted to one
    row per key with ``mapping.aggregate``, then every mapped column is compared
    using its own (or the global) tolerance.
    """
    col_names = [c.name for c in mapping.columns]
    tol = {c.name: mapping.tolerance_for(c) for c in mapping.columns}

    agg_a = _aggregate_mapped(source_a, col_names, mapping.aggregate)
    agg_b = _aggregate_mapped(source_b, col_names, mapping.aggregate)

    a = agg_a.set_index(KEY_COLUMN)
    b = agg_b.set_index(KEY_COLUMN)

    keys_a = set(a.index)
    keys_b = set(b.index)

    result = MappedResult(
        total_a=len(source_a),
        total_b=len(source_b),
        unique_a=len(agg_a),
        unique_b=len(agg_b),
        duplicates_a=len(source_a) - len(agg_a),
        duplicates_b=len(source_b) - len(agg_b),
        columns=col_names,
        aggregate=mapping.aggregate,
    )

    result.only_in_a = sorted(str(k) for k in keys_a - keys_b)
    result.only_in_b = sorted(str(k) for k in keys_b - keys_a)

    for key in sorted(keys_a & keys_b):
        key_clean = True
        for name in col_names:
            va = a.loc[key, name]
            vb = b.loc[key, name]
            va = float(va) if pd.notna(va) else float("nan")
            vb = float(vb) if pd.notna(vb) else float("nan")
            # NaN on either side, or a difference beyond tolerance, is a mismatch.
            if pd.isna(va) or pd.isna(vb) or abs(va - vb) > tol[name]:
                result.mismatches.append(
                    CellMismatch(key=str(key), column=name, value_a=va, value_b=vb)
                )
                key_clean = False
        if key_clean:
            result.matched_keys += 1

    return result

