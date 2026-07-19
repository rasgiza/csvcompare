# score-reconciler

Compare **Name** / **TotalScore** data between two sources (Source A and Source B),
detect mismatches, and generate a plain-text QA report.

## What it does

- Reads `.csv` or `.xlsx`/`.xls` files (column matching is case/space-insensitive).
- Keeps only the `Name` and `TotalScore` columns; ignores everything else.
- Matches rows by `Name` and compares `TotalScore`.
  - Score difference must be `0` (or within `--tolerance`) to count as a match.
  - Any non-zero difference is flagged as a **mismatch**.
- Reports names that exist in only one source (e.g. Source A has a wider date
  range and therefore more rows).
- Writes a human-readable report to a text file for QA follow-up.

## Install

```powershell
cd score-reconciler
pip install -e .
```

## Generate sample data & run

```powershell
python scripts/generate_sample_data.py
score-reconciler data/source_a.xlsx data/source_b.csv -o reconciliation_report.txt
```

Or without installing:

```powershell
python -m score_reconciler.cli data/source_a.xlsx data/source_b.csv
```

## CLI

```
score-reconciler SOURCE_A SOURCE_B [-o OUTPUT] [-t TOLERANCE]
```

| Option | Description | Default |
|--------|-------------|---------|
| `SOURCE_A` | Path to Source A file (`.csv`/`.xlsx`) | required |
| `SOURCE_B` | Path to Source B file (`.csv`/`.xlsx`) | required |
| `-o, --output` | Report file path | `reconciliation_report.txt` |
| `-t, --tolerance` | Allowed absolute score difference | `0.0` |

Exit code is `0` when everything reconciles and `1` when issues are found
(handy for automation/CI).

## Tests

```powershell
pip install -e .[dev]
pytest
```

## Distribute as a standalone app (no Python needed for end users)

Build a self-contained bundle with PyInstaller. End users get a folder they can
run directly — **no Python, no pip, no internet required**.

> PyInstaller cannot cross-compile. Build the **Windows** bundle on Windows and
> the **macOS** bundle on a Mac.

**Windows:**
```powershell
.\build_windows.ps1
# -> dist\score-reconciler\score-reconciler.exe  (zip and share the whole folder)
```

**macOS:**
```bash
./build_macos.sh
# -> dist/score-reconciler/score-reconciler  (zip and share the whole folder)
```

End users run it from the folder:
```powershell
.\score-reconciler.exe "A.xlsx" "B.csv" -o "report.txt"     # Windows
./score-reconciler "A.xlsx" "B.csv" -o "report.txt"          # macOS
```

### onedir vs onefile
- **onedir (default):** a folder with the executable plus libraries. Works under
  hardened corporate policies (Application Control / WDAC) because it does not
  extract DLLs to the temp folder at launch. Distribute the zipped folder.
- **onefile:** a single portable executable that self-extracts to temp at launch.
  More convenient, but some locked-down machines block it.

```powershell
python build_executable.py --mode onefile
```

## Automated builds (GitHub Actions)

Every push to `main` (or a manual run from the **Actions** tab) builds the
standalone bundles for all platforms in the cloud — no local Mac/Windows needed:

- `score-reconciler-windows-amd64` (Intel/AMD Windows)
- `score-reconciler-macos-arm64` (Apple Silicon Macs)
- `score-reconciler-macos-x86_64` (Intel Macs)

Download them from the workflow run's **Artifacts** section, unzip, and send the
matching zip to each user. The workflow is defined in
[.github/workflows/build.yml](.github/workflows/build.yml).


