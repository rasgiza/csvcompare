import pandas as pd

from score_reconciler import Mapping, compare_mapped, load_mapped
from score_reconciler.mapping import conversion_multiplier


def _write_csv(path, headers, rows):
    pd.DataFrame(rows, columns=headers).to_csv(path, index=False)
    return str(path)


def _mapping(**overrides):
    data = {
        "key": {"a": "Name", "b": "foksName"},
        "aggregate": "sum",
        "tolerance": 0.0,
        "columns": [
            {"name": "difhse", "a": "difhse", "b": "difhse"},
            {"name": "shcoes", "a": "shcoes", "b": "shcoes"},
        ],
    }
    data.update(overrides)
    return Mapping.from_dict(data)


def test_conversion_multiplier_units():
    assert conversion_multiplier("min", "sec") == 60.0
    assert conversion_multiplier("hour", "sec") == 3600.0
    assert conversion_multiplier("day", "sec") == 86400.0
    assert conversion_multiplier(None, "sec") == 1.0  # no conversion when unset


def test_pivot_groups_source_b_rows(tmp_path):
    # Source A: one row per key. Source B (Kibana-like): three rows summing to it.
    a = _write_csv(tmp_path / "a.csv", ["Name", "difhse", "shcoes"], [("desm001", 152, 111)])
    b = _write_csv(
        tmp_path / "b.csv",
        ["foksName", "difhse", "shcoes"],
        [("desm001", 54, 45), ("desm001", 54, 34), ("desm001", 44, 32)],
    )
    mapping = _mapping()
    frame_a = load_mapped(a, mapping, side="a")
    frame_b = load_mapped(b, mapping, side="b")
    result = compare_mapped(frame_a, frame_b, mapping)
    # B sums to difhse=152, shcoes=111 -> matches A exactly.
    assert result.matched_keys == 1
    assert not result.has_issues
    assert result.duplicates_b == 2


def test_different_column_names_and_key(tmp_path):
    a = _write_csv(tmp_path / "a.csv", ["Name", "hits"], [("x", 10)])
    b = _write_csv(tmp_path / "b.csv", ["foksName", "count"], [("x", 10)])
    mapping = Mapping.from_dict(
        {
            "key": {"a": "Name", "b": "foksName"},
            "columns": [{"name": "Hits", "a": "hits", "b": "count"}],
        }
    )
    frame_a = load_mapped(a, mapping, side="a")
    frame_b = load_mapped(b, mapping, side="b")
    result = compare_mapped(frame_a, frame_b, mapping)
    assert result.matched_keys == 1
    assert not result.has_issues


def test_unit_conversion_makes_values_match(tmp_path):
    # A reports 2 minutes, B (Kibana) reports 120 seconds -> equal after convert.
    a = _write_csv(tmp_path / "a.csv", ["Name", "elapsed"], [("x", 2)])
    b = _write_csv(tmp_path / "b.csv", ["foksName", "duration"], [("x", 120)])
    mapping = Mapping.from_dict(
        {
            "key": {"a": "Name", "b": "foksName"},
            "columns": [
                {
                    "name": "Duration",
                    "a": "elapsed",
                    "b": "duration",
                    "unit_a": "min",
                    "unit_b": "sec",
                    "to_unit": "sec",
                }
            ],
        }
    )
    frame_a = load_mapped(a, mapping, side="a")
    frame_b = load_mapped(b, mapping, side="b")
    result = compare_mapped(frame_a, frame_b, mapping)
    assert result.matched_keys == 1
    assert not result.has_issues


def test_cell_mismatch_flagged(tmp_path):
    a = _write_csv(tmp_path / "a.csv", ["Name", "difhse", "shcoes"], [("x", 10, 20)])
    b = _write_csv(tmp_path / "b.csv", ["foksName", "difhse", "shcoes"], [("x", 10, 25)])
    result = compare_mapped(
        load_mapped(a, _mapping(), side="a"),
        load_mapped(b, _mapping(), side="b"),
        _mapping(),
    )
    assert result.matched_keys == 0
    assert len(result.mismatches) == 1
    assert result.mismatches[0].column == "shcoes"
    assert result.mismatches[0].difference == -5.0


def test_ms_to_sec_conversion_applied_on_load(tmp_path):
    # 172309.37 ms must load as 172.30937 sec (divided by 1000), not passed raw.
    a = _write_csv(tmp_path / "a.csv", ["Name", "elapsed"], [("x", 172309.37)])
    mapping = Mapping.from_dict(
        {
            "key": {"a": "Name", "b": "foksName"},
            "columns": [
                {
                    "name": "Elapsed",
                    "a": "elapsed",
                    "b": "elapsed",
                    "unit_a": "ms",
                    "unit_b": "sec",
                    "to_unit": "sec",
                }
            ],
        }
    )
    frame_a = load_mapped(a, mapping, side="a")
    assert frame_a["Elapsed"].iloc[0] == 172309.37 / 1000.0  # == 172.30937


def test_missing_to_unit_means_no_conversion(tmp_path):
    # Regression: a unit declared without to_unit must NOT convert (multiplier 1.0).
    a = _write_csv(tmp_path / "a.csv", ["Name", "elapsed"], [("x", 5000)])
    mapping = Mapping.from_dict(
        {
            "key": {"a": "Name", "b": "foksName"},
            "columns": [
                {"name": "Elapsed", "a": "elapsed", "b": "elapsed", "unit_a": "ms"}
            ],
        }
    )
    col = mapping.columns[0]
    assert col.multiplier_a() == 1.0  # no to_unit -> passthrough
    frame_a = load_mapped(a, mapping, side="a")
    assert frame_a["Elapsed"].iloc[0] == 5000  # unchanged, proving the trap


def test_dirty_keys_are_cleaned_and_grouped(tmp_path):
    # Same logical key written with a trailing space, a non-breaking space,
    # a zero-width space and a double space. All must collapse to "TEAM 001"
    # so their values sum into ONE group instead of splitting apart.
    a = _write_csv(tmp_path / "a.csv", ["Name", "difhse", "shcoes"], [("TEAM 001", 30, 30)])
    b = _write_csv(
        tmp_path / "b.csv",
        ["foksName", "difhse", "shcoes"],
        [
            ("TEAM 001 ", 10, 10),          # trailing space
            ("TEAM\u00a0001", 10, 10),      # non-breaking space
            ("TEAM 001\u200b", 5, 5),       # zero-width space
            ("TEAM  001", 5, 5),            # double space
        ],
    )
    mapping = _mapping()
    frame_a = load_mapped(a, mapping, side="a")
    frame_b = load_mapped(b, mapping, side="b")
    # All four B rows collapsed to a single cleaned key.
    assert frame_b["__key__"].nunique() == 1
    assert frame_b["__key__"].iloc[0] == "TEAM 001"
    result = compare_mapped(frame_a, frame_b, mapping)
    # B sums to 30/30 and matches A's single row exactly, no leftover keys.
    assert result.matched_keys == 1
    assert not result.has_issues
    assert result.only_in_b == []

