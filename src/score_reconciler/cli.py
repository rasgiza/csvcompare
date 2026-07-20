"""Command-line interface for score-reconciler."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .comparator import DUPLICATE_STRATEGIES, compare
from .loader import LoaderError, load_source
from .reporter import build_report, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="score-reconciler",
        description=(
            "Compare Name/TotalScore data from two sources (A and B) and "
            "generate a QA mismatch report."
        ),
    )
    parser.add_argument("source_a", help="Path to Source A file (.csv or .xlsx)")
    parser.add_argument("source_b", help="Path to Source B file (.csv or .xlsx)")
    parser.add_argument(
        "-o",
        "--output",
        default="reconciliation_report.txt",
        help="Path for the generated text report (default: reconciliation_report.txt)",
    )
    parser.add_argument(
        "-t",
        "--tolerance",
        type=float,
        default=0.0,
        help="Allowed absolute score difference before flagging a mismatch (default: 0.0)",
    )
    parser.add_argument(
        "-d",
        "--duplicates",
        choices=DUPLICATE_STRATEGIES,
        default="last",
        help=(
            "How to collapse multiple rows with the same name before comparing "
            "(default: last). 'last'/'first' keep a single row per name and take "
            "the score difference; 'sum' totals the scores per name."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        frame_a = load_source(args.source_a)
        frame_b = load_source(args.source_b)
    except LoaderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = compare(
        frame_a,
        frame_b,
        tolerance=args.tolerance,
        duplicate_strategy=args.duplicates,
    )
    report = build_report(
        result,
        source_a_name=Path(args.source_a).name,
        source_b_name=Path(args.source_b).name,
        tolerance=args.tolerance,
    )
    out_path = write_report(report, args.output)

    print(report)
    print(f"\nReport written to: {out_path.resolve()}")

    # Non-zero exit code when issues are found (useful for CI / automation).
    return 1 if result.has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
