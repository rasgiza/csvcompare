import pandas as pd

from score_reconciler import compare, load_source
from score_reconciler.loader import NAME_COLUMN, SCORE_COLUMN


def _write_csv(path, headers, rows):
    pd.DataFrame(rows, columns=headers).to_csv(path, index=False)
    return str(path)


def test_auto_detect_default_columns(tmp_path):
    p = _write_csv(tmp_path / "a.csv", ["Name", "TotalScore"], [("Alice", 10), ("Bob", 20)])
    frame = load_source(p)
    assert list(frame.columns) == [NAME_COLUMN, SCORE_COLUMN]
    assert len(frame) == 2


def test_explicit_custom_column_names(tmp_path):
    p = _write_csv(tmp_path / "a.csv", ["Employee", "Salary"], [("Alice", 100), ("Bob", 200)])
    frame = load_source(p, key="Employee", value="Salary")
    assert frame.loc[frame[NAME_COLUMN] == "Alice", SCORE_COLUMN].iloc[0] == 100


def test_different_column_names_between_sources(tmp_path):
    # Source A uses Candidate/Result, Source B uses Student/Final.
    a = _write_csv(tmp_path / "a.csv", ["Candidate", "Result"], [("Alice", 10), ("Bob", 20)])
    b = _write_csv(tmp_path / "b.csv", ["Student", "Final"], [("Alice", 10), ("Bob", 20)])
    frame_a = load_source(a, key="Candidate", value="Result")
    frame_b = load_source(b, key="Student", value="Final")
    result = compare(frame_a, frame_b)
    assert result.matched == 2
    assert not result.has_issues


def test_multiple_files_are_concatenated(tmp_path):
    a1 = _write_csv(tmp_path / "a1.csv", ["Name", "TotalScore"], [("Alice", 10)])
    a2 = _write_csv(tmp_path / "a2.csv", ["Name", "TotalScore"], [("Bob", 20)])
    b = _write_csv(tmp_path / "b.csv", ["Name", "TotalScore"], [("Alice", 10), ("Bob", 20)])
    frame_a = load_source([a1, a2])
    frame_b = load_source(b)
    assert len(frame_a) == 2
    result = compare(frame_a, frame_b)
    assert result.matched == 2
    assert not result.has_issues
