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
            "Compare a key/value dataset between two sources (A and B) and "
            "generate a reconciliation report. Rows are matched on a KEY column "
            "and a VALUE column is compared. Columns can have any name, can "
            "differ between the two sources, and each source may span several "
            "files."
        ),
    )
    # Simple positional form: exactly one file per source.
    parser.add_argument(
        "source_a",
        nargs="?",
        help="Path to Source A file (.csv/.tsv/.xlsx). For multiple files use -a.",
    )
    parser.add_argument(
        "source_b",
        nargs="?",
        help="Path to Source B file (.csv/.tsv/.xlsx). For multiple files use -b.",
    )
    # Multi-file form: one or more files per source.
    parser.add_argument(
        "-a",
        "--source-a",
        nargs="+",
        dest="a_files",
        metavar="FILE",
        help="One or more Source A files (stacked/concatenated).",
    )
    parser.add_argument(
        "-b",
        "--source-b",
        nargs="+",
        dest="b_files",
        metavar="FILE",
        help="One or more Source B files (stacked/concatenated).",
    )
    # Column selection.
    parser.add_argument(
        "--key",
        help="Column name to match rows on, for BOTH sources (auto-detected if omitted).",
    )
    parser.add_argument("--key-a", help="Key column name in Source A (overrides --key).")
    parser.add_argument("--key-b", help="Key column name in Source B (overrides --key).")
    parser.add_argument(
        "--value",
        help="Column name to compare, for BOTH sources (auto-detected if omitted).",
    )
    parser.add_argument("--value-a", help="Value column name in Source A (overrides --value).")
    parser.add_argument("--value-b", help="Value column name in Source B (overrides --value).")
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
        help="Allowed absolute value difference before flagging a mismatch (default: 0.0)",
    )
    parser.add_argument(
        "-d",
        "--duplicates",
        choices=DUPLICATE_STRATEGIES,
        default="last",
        help=(
            "How to collapse multiple rows with the same key before comparing "
            "(default: last). 'last'/'first' keep a single row per key and take "
            "the value difference; 'sum' totals the values per key."
        ),
    )
    return parser


def _describe(paths: list[str]) -> str:
    if len(paths) == 1:
        return Path(paths[0]).name
    return f"{len(paths)} files: " + ", ".join(Path(p).name for p in paths)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Resolve source files from either the positional or the -a/-b form.
    a_files = args.a_files or ([args.source_a] if args.source_a else None)
    b_files = args.b_files or ([args.source_b] if args.source_b else None)
    if not a_files or not b_files:
        parser.error(
            "Provide Source A and Source B. Either two positional files "
            "(A.csv B.csv) or the -a/-b flags for multiple files."
        )

    key_a = args.key_a or args.key
    key_b = args.key_b or args.key
    value_a = args.value_a or args.value
    value_b = args.value_b or args.value

    try:
        frame_a = load_source(a_files, key=key_a, value=value_a)
        frame_b = load_source(b_files, key=key_b, value=value_b)
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
        source_a_name=_describe(a_files),
        source_b_name=_describe(b_files),
        tolerance=args.tolerance,
        key_label=(args.key or args.key_a or args.key_b or "Name"),
        value_label=(args.value or args.value_a or args.value_b or "Score"),
    )
    out_path = write_report(report, args.output)

    print(report)
    print(f"\nReport written to: {out_path.resolve()}")

    # Non-zero exit code when issues are found (useful for CI / automation).
    return 1 if result.has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
