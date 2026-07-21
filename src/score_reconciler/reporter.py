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
    key_label: str = "Name",
    value_label: str = "Score",
) -> str:
    """Return the full QA report as a string."""
    lines: list[str] = []
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append(_LINE)
    lines.append("RECONCILIATION REPORT")
    lines.append(_LINE)
    lines.append(f"Generated : {stamp}")
    lines.append(f"Source A  : {source_a_name}")
    lines.append(f"Source B  : {source_b_name}")
    lines.append(f"Key column   : {key_label} (rows are matched on this)")
    lines.append(f"Value column : {value_label} (this is compared)")
    lines.append(f"Tolerance : {tolerance} (value difference must be <= this to match)")
    lines.append("")

    # ---- Summary -----------------------------------------------------------
    lines.append("SUMMARY")
    lines.append(_SUBLINE)
    lines.append(f"Rows in Source A         : {result.total_a}")
    lines.append(f"Rows in Source B         : {result.total_b}")
    lines.append(f"Duplicate strategy       : {result.strategy} (rows sharing a key are collapsed)")
    lines.append(f"Unique keys in Source A  : {result.unique_a} ({result.duplicates_a} duplicate row(s) collapsed)")
    lines.append(f"Unique keys in Source B  : {result.unique_b} ({result.duplicates_b} duplicate row(s) collapsed)")
    lines.append(f"Row counts match         : {'YES' if result.row_count_matches else 'NO'}")
    lines.append(f"Keys matched cleanly     : {result.matched}")
    lines.append(f"Value mismatches         : {len(result.mismatches)}")
    lines.append(f"Only in Source A         : {len(result.only_in_a)}")
    lines.append(f"Only in Source B         : {len(result.only_in_b)}")
    lines.append("")

    verdict = "PASS - no issues found" if not result.has_issues else "FAIL - issues require QA review"
    lines.append(f"OVERALL RESULT: {verdict}")
    lines.append("")

    # ---- Value mismatches --------------------------------------------------
    lines.append(f"VALUE MISMATCHES ({key_label} matched, {value_label} difference > tolerance)")
    lines.append(_SUBLINE)
    if result.mismatches:
        lines.append(f"{key_label:<30}{'Source A':>12}{'Source B':>12}{'Diff':>12}")
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
        lines.append(f"{key_label:<30}{value_label:>12}")
        for r in result.only_in_a:
            lines.append(f"{r.name:<30}{r.score:>12.2f}")
    else:
        lines.append("None.")
    lines.append("")

    # ---- Only in B ---------------------------------------------------------
    lines.append("ROWS ONLY IN SOURCE B (missing from Source A)")
    lines.append(_SUBLINE)
    if result.only_in_b:
        lines.append(f"{key_label:<30}{value_label:>12}")
        for r in result.only_in_b:
            lines.append(f"{r.name:<30}{r.score:>12.2f}")
    else:
        lines.append("None.")
    lines.append("")

    # ---- QA guidance -------------------------------------------------------
    lines.append("QA NOTES")
    lines.append(_SUBLINE)
    if not result.has_issues:
        lines.append("All keys and values reconcile. No further action needed.")
    else:
        if result.mismatches:
            lines.append(
                f"- {len(result.mismatches)} key(s) have differing {value_label} values. Verify "
                "which source is authoritative and confirm the correct value."
            )
        if result.only_in_a:
            lines.append(
                f"- {len(result.only_in_a)} key(s) exist only in Source A. This may be "
                "expected if Source A covers a wider range; confirm the range."
            )
        if result.only_in_b:
            lines.append(
                f"- {len(result.only_in_b)} key(s) exist only in Source B. Investigate why "
                "these are missing from Source A."
            )
    lines.append(_LINE)

    return "\n".join(lines)


def build_mapped_report(
    result,
    mapping,
    source_a_name: str,
    source_b_name: str,
) -> str:
    """Return the report for a mapped (multi-column) comparison."""
    lines: list[str] = []
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append(_LINE)
    lines.append("RECONCILIATION REPORT (mapped, multi-column)")
    lines.append(_LINE)
    lines.append(f"Generated : {stamp}")
    lines.append(f"Source A  : {source_a_name}")
    lines.append(f"Source B  : {source_b_name}")
    lines.append(f"Key       : A='{mapping.key_a}'  B='{mapping.key_b}'")
    lines.append(f"Aggregate : {mapping.aggregate} (rows sharing a key are collapsed/pivoted)")
    lines.append("")

    # ---- Column map --------------------------------------------------------
    lines.append("COLUMN MAP")
    lines.append(_SUBLINE)
    lines.append(f"{'Report name':<20}{'Source A':<18}{'Source B':<18}{'Unit A>Unit B':<16}{'Tol':>6}")
    for col in mapping.columns:
        unit = "-"
        if col.to_unit and (col.unit_a or col.unit_b):
            unit = f"{col.unit_a or '?'}>{col.to_unit},{col.unit_b or '?'}>{col.to_unit}"
        tol = mapping.tolerance_for(col)
        lines.append(f"{col.name:<20}{col.source_a:<18}{col.source_b:<18}{unit:<16}{tol:>6.2f}")
    lines.append("")

    # ---- Summary -----------------------------------------------------------
    lines.append("SUMMARY")
    lines.append(_SUBLINE)
    lines.append(f"Rows in Source A         : {result.total_a}")
    lines.append(f"Rows in Source B         : {result.total_b}")
    lines.append(f"Unique keys in Source A  : {result.unique_a} ({result.duplicates_a} row(s) collapsed)")
    lines.append(f"Unique keys in Source B  : {result.unique_b} ({result.duplicates_b} row(s) collapsed)")
    lines.append(f"Keys matched cleanly     : {result.matched_keys}")
    lines.append(f"Cell mismatches          : {len(result.mismatches)}")
    lines.append(f"Keys only in Source A    : {len(result.only_in_a)}")
    lines.append(f"Keys only in Source B    : {len(result.only_in_b)}")
    lines.append("")

    verdict = "PASS - no issues found" if not result.has_issues else "FAIL - issues require review"
    lines.append(f"OVERALL RESULT: {verdict}")
    lines.append("")

    # ---- Cell mismatches ---------------------------------------------------
    lines.append("CELL MISMATCHES (key matched, a column value differs beyond tolerance)")
    lines.append(_SUBLINE)
    if result.mismatches:
        lines.append(f"{'Key':<24}{'Column':<18}{'Source A':>14}{'Source B':>14}{'Diff':>14}")
        for m in result.mismatches:
            lines.append(
                f"{m.key:<24}{m.column:<18}{m.value_a:>14.2f}{m.value_b:>14.2f}{m.difference:>14.2f}"
            )
    else:
        lines.append("None.")
    lines.append("")

    # ---- Only in A / B -----------------------------------------------------
    lines.append("KEYS ONLY IN SOURCE A (missing from Source B)")
    lines.append(_SUBLINE)
    lines.append(", ".join(result.only_in_a) if result.only_in_a else "None.")
    lines.append("")

    lines.append("KEYS ONLY IN SOURCE B (missing from Source A)")
    lines.append(_SUBLINE)
    lines.append(", ".join(result.only_in_b) if result.only_in_b else "None.")
    lines.append("")

    # ---- QA guidance -------------------------------------------------------
    lines.append("QA NOTES")
    lines.append(_SUBLINE)
    if not result.has_issues:
        lines.append("All keys and mapped columns reconcile. No further action needed.")
    else:
        if result.mismatches:
            lines.append(
                f"- {len(result.mismatches)} cell value(s) differ. Check the column map "
                "(names/units) and confirm which source is authoritative."
            )
        if result.only_in_a:
            lines.append(f"- {len(result.only_in_a)} key(s) exist only in Source A.")
        if result.only_in_b:
            lines.append(f"- {len(result.only_in_b)} key(s) exist only in Source B.")
    lines.append(_LINE)

    return "\n".join(lines)


def write_report(report_text: str, output_path: str | Path) -> Path:
    """Write the report to a text file and return the path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    return output_path
