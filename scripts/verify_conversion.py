"""Diagnose unit conversion in a mapping.

For every column in a mapping it prints the declared units, the resulting
multiplier, and whether that column will actually be converted or passed
through unchanged. Optionally, given the real source files, it shows the raw
value next to the converted value for the first row of each key so you can see
the division happen (or not).

Usage::

    python scripts/verify_conversion.py MAPPING.json
    python scripts/verify_conversion.py MAPPING.json --source-a A.csv --source-b B.csv

Exit code is 1 if any column declares a unit but is NOT actually converting
(e.g. a time column missing ``to_unit``), so it can be used as a check.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running from the repo root without installing.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from score_reconciler.mapping import Mapping  # noqa: E402


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    return str(value)


def _sample_raw_converted(path: str, header: str, multiplier: float) -> tuple[str, str]:
    """Return (raw, converted) as strings for the first numeric value found."""
    suffix = Path(path).suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        frame = pd.read_excel(path)
    else:
        frame = pd.read_csv(path, sep="\t" if suffix == ".tsv" else None, engine="python")

    # Case/space-insensitive header match.
    norm = {"".join(str(c).lower().split()): c for c in frame.columns}
    key = "".join(str(header).lower().split())
    if key not in norm:
        return ("<header not found>", "-")
    series = pd.to_numeric(frame[norm[key]], errors="coerce").dropna()
    if series.empty:
        return ("<no numeric values>", "-")
    raw = float(series.iloc[0])
    return (f"{raw:g}", f"{raw * multiplier:g}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify unit conversion in a mapping.")
    parser.add_argument("mapping", help="Path to the mapping.json file.")
    parser.add_argument("--source-a", help="Optional Source A file to sample raw vs converted values.")
    parser.add_argument("--source-b", help="Optional Source B file to sample raw vs converted values.")
    args = parser.parse_args(argv)

    mapping = Mapping.from_file(args.mapping)

    print("=" * 100)
    print(f"CONVERSION CHECK for {args.mapping}")
    print(f"Key: A='{mapping.key_a}'  B='{mapping.key_b}'   Aggregate: {mapping.aggregate}")
    print("=" * 100)

    header = (
        f"{'Column':<16}{'Side':<5}{'Header':<18}{'unit':<8}{'to_unit':<9}"
        f"{'x mult':<10}{'converts?':<11}"
    )
    print(header)
    print("-" * 100)

    problems = 0
    for col in mapping.columns:
        for side, src_header, unit, mult, src_path in (
            ("A", col.source_a, col.unit_a, col.multiplier_a(), args.source_a),
            ("B", col.source_b, col.unit_b, col.multiplier_b(), args.source_b),
        ):
            declared_unit = unit is not None
            converts = mult != 1.0
            # A column that declares a unit but has multiplier 1.0 is suspicious:
            # either to_unit is missing or unit == to_unit (both -> no change).
            suspicious = declared_unit and not converts and (col.to_unit is None)
            status = "YES" if converts else ("MISSING to_unit" if suspicious else "no (raw)")
            if suspicious:
                problems += 1

            line = (
                f"{col.name:<16}{side:<5}{_fmt(src_header):<18}{_fmt(unit):<8}"
                f"{_fmt(col.to_unit):<9}{mult:<10g}{status:<11}"
            )

            sample = ""
            src_path_side = src_path
            if src_path_side:
                raw, conv = _sample_raw_converted(src_path_side, src_header, mult)
                sample = f"  e.g. raw={raw} -> {conv}"
            print(line + sample)
        print("-" * 100)

    if problems:
        print(f"\nRESULT: {problems} column-side(s) declare a unit but are NOT converting "
              f"(missing 'to_unit'). Add \"to_unit\": \"sec\" to those columns.")
        return 1
    print("\nRESULT: OK - every column with a declared unit is converting as expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
