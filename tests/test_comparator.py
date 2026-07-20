import pandas as pd

from score_reconciler import compare
from score_reconciler.loader import NAME_COLUMN, SCORE_COLUMN


def _frame(rows):
    return pd.DataFrame(rows, columns=[NAME_COLUMN, SCORE_COLUMN])


def test_all_match():
    a = _frame([("Alice", 10), ("Bob", 20)])
    b = _frame([("Alice", 10), ("Bob", 20)])
    result = compare(a, b)
    assert result.matched == 2
    assert not result.has_issues


def test_score_mismatch_flagged():
    a = _frame([("Alice", 10), ("Bob", 20)])
    b = _frame([("Alice", 10), ("Bob", 25)])
    result = compare(a, b)
    assert len(result.mismatches) == 1
    assert result.mismatches[0].name == "Bob"
    assert result.mismatches[0].difference == -5
    assert result.has_issues


def test_only_in_a_when_source_a_has_more_rows():
    a = _frame([("Alice", 10), ("Bob", 20), ("Carol", 30)])
    b = _frame([("Alice", 10), ("Bob", 20)])
    result = compare(a, b)
    assert [r.name for r in result.only_in_a] == ["Carol"]
    assert result.only_in_b == []
    assert not result.row_count_matches


def test_only_in_b():
    a = _frame([("Alice", 10)])
    b = _frame([("Alice", 10), ("Zoe", 99)])
    result = compare(a, b)
    assert [r.name for r in result.only_in_b] == ["Zoe"]


def test_tolerance_allows_small_diff():
    a = _frame([("Alice", 10.0)])
    b = _frame([("Alice", 10.4)])
    assert compare(a, b, tolerance=0.5).matched == 1
    assert len(compare(a, b, tolerance=0.0).mismatches) == 1


def test_duplicate_names_collapsed_to_one_by_default():
    # Alice is listed twice with the SAME score in A; B lists her once.
    # Default keeps one row per name and takes the difference (89 - 89 = 0).
    a = _frame([("Alice", 89), ("Alice", 89), ("Bob", 100)])
    b = _frame([("Alice", 89), ("Bob", 100)])
    result = compare(a, b)
    assert result.matched == 2
    assert not result.has_issues
    assert result.duplicates_a == 1
    assert result.unique_a == 2


def test_duplicate_names_summed_with_sum_strategy():
    # Opt-in: sum totals each name's scores before comparing.
    a = _frame([("Alice", 10), ("Alice", 15), ("Bob", 20)])
    b = _frame([("Alice", 25), ("Bob", 20)])
    result = compare(a, b, duplicate_strategy="sum")
    assert result.matched == 2
    assert not result.has_issues


def test_duplicate_strategy_last_keeps_final_row():
    a = _frame([("Alice", 10), ("Alice", 15)])
    b = _frame([("Alice", 15)])
    result = compare(a, b, duplicate_strategy="last")
    assert result.matched == 1
    assert not result.has_issues
