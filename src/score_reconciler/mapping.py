"""Mapping configuration for multi-column reconciliation.

A **mapping** describes how to reconcile two sources whose columns differ in
name, unit, and shape. It carries three things the plain key/value mode cannot:

1. **Many columns at once** - compare several metric columns per key in one run.
2. **Per-column name mapping** - column ``elapsed`` in Source A is the same data
   as ``duration`` in Source B.
3. **Unit normalization** - convert a time column expressed in sec/min/hour/day
   to a common unit (default seconds) so it lines up with a source (e.g. Kibana)
   that always reports seconds.

It also names the key column per source and the aggregation used to pivot
(group) multiple rows per key down to one row before comparing.

Schema (JSON)::

    {
      "key":       { "a": "Name",   "b": "foksName" },
      "aggregate": "sum",
      "tolerance": 0.0,
      "columns": [
        { "name": "difhse",  "a": "difhse",  "b": "difhse" },
        { "name": "Duration","a": "elapsed", "b": "duration",
          "unit_a": "min", "unit_b": "sec", "to_unit": "sec",
          "tolerance": 0.5 }
      ]
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Time units expressed as seconds. Used to normalize a column to a common unit.
_TIME_FACTORS: dict[str, float] = {
    "ms": 0.001, "millisecond": 0.001, "milliseconds": 0.001,
    "s": 1.0, "sec": 1.0, "secs": 1.0, "second": 1.0, "seconds": 1.0,
    "m": 60.0, "min": 60.0, "mins": 60.0, "minute": 60.0, "minutes": 60.0,
    "h": 3600.0, "hr": 3600.0, "hrs": 3600.0, "hour": 3600.0, "hours": 3600.0,
    "d": 86400.0, "day": 86400.0, "days": 86400.0,
}

# Aggregations allowed when collapsing multiple rows per key (the "pivot").
AGGREGATIONS = ("sum", "mean", "last", "first", "max", "min", "count")


class MappingError(Exception):
    """Raised when a mapping file is missing, malformed, or uses unknown units."""


def _unit_factor(unit: str) -> float:
    key = "".join(str(unit).lower().split())
    if key not in _TIME_FACTORS:
        raise MappingError(
            f"Unknown time unit '{unit}'. Supported units: "
            f"{sorted(set(_TIME_FACTORS))}"
        )
    return _TIME_FACTORS[key]


def conversion_multiplier(from_unit: str | None, to_unit: str | None) -> float:
    """Return the factor that converts a value from ``from_unit`` to ``to_unit``.

    ``value_in_to_unit = value_in_from_unit * multiplier``. When either unit is
    omitted, no conversion is applied (multiplier ``1.0``).
    """
    if not from_unit or not to_unit:
        return 1.0
    return _unit_factor(from_unit) / _unit_factor(to_unit)


@dataclass
class ColumnMap:
    """One metric column to compare, mapped across the two sources."""

    name: str                     # friendly label shown in the report
    source_a: str                 # column header in Source A
    source_b: str                 # column header in Source B
    unit_a: str | None = None     # unit of the Source A column (e.g. "min")
    unit_b: str | None = None     # unit of the Source B column (e.g. "sec")
    to_unit: str | None = None    # common unit to convert both to (e.g. "sec")
    tolerance: float | None = None  # per-column tolerance; falls back to global

    def multiplier_a(self) -> float:
        return conversion_multiplier(self.unit_a, self.to_unit)

    def multiplier_b(self) -> float:
        return conversion_multiplier(self.unit_b, self.to_unit)


@dataclass
class Mapping:
    """A full reconciliation mapping."""

    key_a: str
    key_b: str
    columns: list[ColumnMap] = field(default_factory=list)
    aggregate: str = "sum"
    tolerance: float = 0.0

    def tolerance_for(self, column: ColumnMap) -> float:
        return self.tolerance if column.tolerance is None else column.tolerance

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mapping":
        if not isinstance(data, dict):
            raise MappingError("Mapping must be a JSON object.")

        key = data.get("key")
        if not isinstance(key, dict) or not key.get("a") or not key.get("b"):
            raise MappingError(
                'Mapping needs a "key" object with "a" and "b" column names, '
                'e.g. "key": {"a": "Name", "b": "foksName"}.'
            )

        raw_columns = data.get("columns")
        if not isinstance(raw_columns, list) or not raw_columns:
            raise MappingError('Mapping needs a non-empty "columns" list.')

        aggregate = data.get("aggregate", "sum")
        if aggregate not in AGGREGATIONS:
            raise MappingError(
                f"Unknown aggregate '{aggregate}'. Choose one of: "
                f"{', '.join(AGGREGATIONS)}"
            )

        columns: list[ColumnMap] = []
        for i, col in enumerate(raw_columns):
            if not isinstance(col, dict):
                raise MappingError(f"columns[{i}] must be an object.")
            source_a = col.get("a")
            source_b = col.get("b")
            if not source_a or not source_b:
                raise MappingError(
                    f'columns[{i}] needs "a" and "b" column names.'
                )
            columns.append(
                ColumnMap(
                    name=str(col.get("name") or source_a),
                    source_a=str(source_a),
                    source_b=str(source_b),
                    unit_a=col.get("unit_a"),
                    unit_b=col.get("unit_b"),
                    to_unit=col.get("to_unit"),
                    tolerance=(
                        float(col["tolerance"]) if col.get("tolerance") is not None else None
                    ),
                )
            )

        # Validate units eagerly so errors surface before any file is read.
        for col in columns:
            col.multiplier_a()
            col.multiplier_b()

        return cls(
            key_a=str(key["a"]),
            key_b=str(key["b"]),
            columns=columns,
            aggregate=aggregate,
            tolerance=float(data.get("tolerance", 0.0)),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "Mapping":
        path = Path(path)
        if not path.exists():
            raise MappingError(f"Mapping file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MappingError(f"Mapping file is not valid JSON: {exc}") from exc
        return cls.from_dict(data)
