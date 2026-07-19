"""Human-readable QA report generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .comparator import ComparisonResult

_LINE = "=" * 70
_SUBLINE = "-" * 70


def build_report(
    result: ComparisonResult,
    source_a_name: str,
    source_b_name: str,
    tolerance: float = 0.0,
) -> str:
    """Return the full QA report as a string."""
    lines: list[str] = []
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append(_LINE)
    lines.append("SCORE RECONCILIATION REPORT")
    lines.append(_LINE)
    lines.append(f"Generated : {stamp}")
    lines.append(f"Source A  : {source_a_name}")
    lines.append(f"Source B  : {source_b_name}")
    lines.append(f"Tolerance : {tolerance} (score difference must be <= this to match)")
    lines.append("")

    # ---- Summary -----------------------------------------------------------
    lines.append("SUMMARY")
    lines.append(_SUBLINE)
    lines.append(f"Rows in Source A         : {result.total_a}")
    lines.append(f"Rows in Source B         : {result.total_b}")
    lines.append(f"Row counts match         : {'YES' if result.row_count_matches else 'NO'}")
    lines.append(f"Names matched cleanly    : {result.matched}")
    lines.append(f"Score mismatches         : {len(result.mismatches)}")
    lines.append(f"Only in Source A         : {len(result.only_in_a)}")
    lines.append(f"Only in Source B         : {len(result.only_in_b)}")
    lines.append("")

    verdict = "PASS - no issues found" if not result.has_issues else "FAIL - issues require QA review"
    lines.append(f"OVERALL RESULT: {verdict}")
    lines.append("")

    # ---- Score mismatches --------------------------------------------------
    lines.append("SCORE MISMATCHES (name matched, score difference > tolerance)")
    lines.append(_SUBLINE)
    if result.mismatches:
        lines.append(f"{'Name':<30}{'Source A':>12}{'Source B':>12}{'Diff':>12}")
        for m in result.mismatches:
            lines.append(
                f"{m.name:<30}{m.score_a:>12.2f}{m.score_b:>12.2f}{m.difference:>12.2f}"
            )
    else:
        lines.append("None.")
    lines.append("")

    # ---- Only in A ---------------------------------------------------------
    lines.append("ROWS ONLY IN SOURCE A (missing from Source B)")
    lines.append(_SUBLINE)
    if result.only_in_a:
        lines.append(f"{'Name':<30}{'Score':>12}")
        for r in result.only_in_a:
            lines.append(f"{r.name:<30}{r.score:>12.2f}")
    else:
        lines.append("None.")
    lines.append("")

    # ---- Only in B ---------------------------------------------------------
    lines.append("ROWS ONLY IN SOURCE B (missing from Source A)")
    lines.append(_SUBLINE)
    if result.only_in_b:
        lines.append(f"{'Name':<30}{'Score':>12}")
        for r in result.only_in_b:
            lines.append(f"{r.name:<30}{r.score:>12.2f}")
    else:
        lines.append("None.")
    lines.append("")

    # ---- QA guidance -------------------------------------------------------
    lines.append("QA NOTES")
    lines.append(_SUBLINE)
    if not result.has_issues:
        lines.append("All names and scores reconcile. No further action needed.")
    else:
        if result.mismatches:
            lines.append(
                f"- {len(result.mismatches)} name(s) have differing scores. Verify which "
                "source is authoritative and confirm the correct TotalScore."
            )
        if result.only_in_a:
            lines.append(
                f"- {len(result.only_in_a)} name(s) exist only in Source A. This may be "
                "expected if Source A covers a wider date range; confirm the range."
            )
        if result.only_in_b:
            lines.append(
                f"- {len(result.only_in_b)} name(s) exist only in Source B. Investigate why "
                "these are missing from Source A."
            )
    lines.append(_LINE)

    return "\n".join(lines)


def write_report(report_text: str, output_path: str | Path) -> Path:
    """Write the report to a text file and return the path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    return output_path
