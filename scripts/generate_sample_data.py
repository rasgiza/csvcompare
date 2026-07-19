"""Generate fake Source A and Source B data to demonstrate/test the reconciler.

Run:  python scripts/generate_sample_data.py
Creates:
  data/source_a.xlsx  (Excel, wider date range -> more rows, has extra columns)
  data/source_b.csv   (CSV, fewer rows, with a couple of deliberate score mismatches)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Source A: the "system of record" with a wider date range and many columns.
    source_a = pd.DataFrame(
        {
            "Id": range(1, 9),
            "Name": [
                "Alice Johnson",
                "Bob Smith",
                "Carla Diaz",
                "David Lee",
                "Emma Brown",
                "Frank Nguyen",
                "Grace Kim",
                "Henry Adams",
            ],
            "Department": ["Ops"] * 8,
            "TotalScore": [95, 88, 72, 100, 64, 81, 90, 77],
            "Date": pd.date_range("2026-01-01", periods=8, freq="D"),
        }
    )

    # Source B: fewer rows (narrower date range) + 2 intentional score mismatches.
    #  - Bob Smith    : 88 -> 85   (mismatch, diff 3)
    #  - Emma Brown   : 64 -> 70   (mismatch, diff -6)
    #  - Henry Adams  : dropped    (only in A)
    #  - Zoe Martinez : added      (only in B)
    source_b = pd.DataFrame(
        {
            "Name": [
                "Alice Johnson",
                "Bob Smith",
                "Carla Diaz",
                "David Lee",
                "Emma Brown",
                "Frank Nguyen",
                "Grace Kim",
                "Zoe Martinez",
            ],
            "TotalScore": [95, 85, 72, 100, 70, 81, 90, 66],
        }
    )

    a_path = DATA_DIR / "source_a.xlsx"
    b_path = DATA_DIR / "source_b.csv"
    source_a.to_excel(a_path, index=False)
    source_b.to_csv(b_path, index=False)

    print(f"Wrote {a_path}")
    print(f"Wrote {b_path}")


if __name__ == "__main__":
    main()
