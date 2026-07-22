# Kibana vs. Ops-spreadsheet scenario

A worked example that exercises **every** feature of the mapping-based
(multi-column) reconciliation mode at once.

## The story

An operations team keeps a hand-maintained spreadsheet of nightly ETL jobs
(`source_a_ops.csv`). A separate Kibana export (`kibana_logs.csv`) captures the
same jobs from the logging pipeline. The two sources **disagree in three ways**,
and this scenario proves the tool copes with all of them:

1. **Different field names** — the spreadsheet uses friendly names
   (`JobName`, `RowsIn`, `ExtractTime`); Kibana uses log field names
   (`kib_job`, `rows_in`, `extract_secs`).
2. **Different time units** — the spreadsheet records durations in **minutes,
   hours, and days**; Kibana records everything in **seconds**. The mapping
   converts Source A to seconds before comparing.
3. **One row per job vs. many** — Kibana emits one log line per run, so each job
   appears multiple times. `aggregate: "sum"` pivots those rows back down to one
   row per job before comparing.

## The column map (`mapping.json`)

| Meaning        | Source A (`JobName` key) | Source B (`kib_job` key) | Unit conversion |
| -------------- | ------------------------ | ------------------------ | --------------- |
| Rows ingested  | `RowsIn`                 | `rows_in`                | count           |
| Rejected rows  | `RowsRejected`           | `rows_rejected`          | count           |
| Extract time   | `ExtractTime` (minutes)  | `extract_secs`           | min → sec       |
| Load time      | `LoadTime` (hours)       | `load_secs`              | hour → sec      |
| Archive window | `ArchiveWindow` (days)   | `archive_secs`           | day → sec       |

## What the result should show

- **`etl_orders`** — clean match. 3 Kibana rows sum to the sheet's totals;
  5 min → 300 s, 0.5 h → 1800 s, 30 days → 2,592,000 s all line up.
- **`etl_inventory`** — clean match. 4 Kibana rows summed.
- **`etl_customers`** — one **cell mismatch**: sheet says `RowsRejected = 5`,
  Kibana sums to `4` (diff `1.0`, beyond the `0.5` tolerance).
- **`etl_returns`** — only in Source A (missing from Kibana).
- **`etl_audit`** — only in Source B (missing from the sheet).

Final tally: **2 clean, 1 cell mismatch, 1 only-in-A, 1 only-in-B** → exit code `1`.

## Run it

From the `score-reconciler` folder:

```powershell
score-reconciler examples/kibana-scenario/source_a_ops.csv `
                 examples/kibana-scenario/kibana_logs.csv `
                 -m examples/kibana-scenario/mapping.json `
                 -o examples/kibana-scenario/report.txt
```

Or from source:

```powershell
python -m score_reconciler.cli examples/kibana-scenario/source_a_ops.csv `
                               examples/kibana-scenario/kibana_logs.csv `
                               -m examples/kibana-scenario/mapping.json `
                               -o examples/kibana-scenario/report.txt
```

The generated report is saved as `report.txt` in this folder.
