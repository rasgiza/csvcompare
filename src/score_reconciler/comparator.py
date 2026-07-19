"""Comparison logic between Source A and Source B.

We match rows by ``Name`` and compare ``TotalScore``. The score difference
must be exactly 0 to count as a match; any non-zero absolute difference is a
mismatch. Names that exist in only one source are reported separately so QA
can investigate row-count differences (e.g. caused by different date ranges).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .loader import NAME_COLUMN, SCORE_COLUMN


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
    strategy: str = "sum"
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
    duplicate_strategy: str = "sum",
) -> ComparisonResult:
    """Compare two normalized source frames.

    Args:
        source_a: Normalized frame from Source A.
        source_b: Normalized frame from Source B.
        tolerance: Allowed absolute score difference. Default 0.0 means any
            non-zero difference is flagged.
        duplicate_strategy: How to collapse rows that share the same name
            before comparing (``sum`` by default). See ``DUPLICATE_STRATEGIES``.
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
