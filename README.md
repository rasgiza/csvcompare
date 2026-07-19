# score-reconciler

Compare a **Name** / **TotalScore** dataset from two sources (Source A and
Source B), find any mismatches, and write a plain-text QA report.

There are **two ways to use this tool**:

1. **End users** — run a prebuilt app. No Python, no setup. → [Jump to "For end users"](#for-end-users)
2. **Developers** — run from source or build the app. → [Jump to "For developers"](#for-developers)

---

## What it does

- Reads `.csv` or `.xlsx`/`.xls` files. Column names are matched
  case/space-insensitively (`TotalScore`, `total score`, `Score` all work).
- Uses only the `Name` and `TotalScore` columns; every other column is ignored.
- Matches rows by `Name`, then compares `TotalScore`:
  - Difference of `0` (or within `--tolerance`) = **match**.
  - Any non-zero difference = **mismatch** (flagged in the report).
- Lists names found in only one source (e.g. Source A covers a wider date range
  and has extra rows).
- Writes a human-readable report you can hand to QA.

The exit code is `0` when everything reconciles, `1` when any issue is found.

---

## For end users

You do **not** need Python. You just need the prebuilt app for your operating
system.

### 1. Get the app

Download the zip for your platform from the project's **GitHub Actions** builds:

1. Open **https://github.com/rasgiza/csvcompare/actions**
2. Click the most recent successful run (green check).
3. Under **Artifacts**, download the one that matches your machine:
   - `score-reconciler-windows-amd64` — Windows (Intel/AMD)
   - `score-reconciler-macos-arm64` — Mac (Apple Silicon: M1/M2/M3/M4)
   - `score-reconciler-macos-x86_64` — Mac (older Intel)

### 2. Unzip it

Unzip the downloaded file. You get a folder named `score-reconciler`.
**Keep the folder together** — the program needs the files next to it.

### 3. Run it

Open a terminal **inside the unzipped folder** and run:

**Windows (PowerShell):**
```powershell
.\score-reconciler.exe "C:\path\to\SourceA.xlsx" "C:\path\to\SourceB.csv" -o "C:\path\to\report.txt"
```

**Mac (Terminal):**
```bash
# First run only: clear Apple's "unidentified developer" block
xattr -dr com.apple.quarantine ./score-reconciler

./score-reconciler "/path/to/SourceA.xlsx" "/path/to/SourceB.csv" -o "/path/to/report.txt"
```

- The **first** file path is Source A, the **second** is Source B.
- The report is written to the path after `-o`. Open that `.txt` file to see the
  results.

That's it.

---

## For developers

### Run from source

**Recommended (works everywhere, avoids old-pip errors) — use a virtual environment:**

```bash
git clone https://github.com/rasgiza/csvcompare.git
cd csvcompare

python3 -m venv .venv          # "python" on Windows
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
```

> **Why the venv?** A system Python often ships an old `pip` that can't do an
> editable (`-e`) install and can't write to site-packages, which produces
> errors like *"Directory cannot be installed in editable mode"* or
> *"site-packages is not writeable"*. A venv gives you a fresh, writable,
> upgradeable pip.

**No editable install needed?** Just install the dependencies and run the tool:

```bash
pip install -r requirements.txt          # runtime only (pandas, openpyxl)
# or, for tests + building the app too:
pip install -r requirements-dev.txt
```

(Dependencies are declared once in `pyproject.toml`; the `requirements*.txt`
files mirror them for a simpler, old-pip-friendly install.)

Generate sample data and try it:

```bash
python scripts/generate_sample_data.py
score-reconciler data/source_a.xlsx data/source_b.csv -o reconciliation_report.txt
```

(Or run without installing: `python -m score_reconciler.cli A.csv B.csv`.)

### Command reference

```
score-reconciler SOURCE_A SOURCE_B [-o OUTPUT] [-t TOLERANCE]
```

| Argument / option | Description | Default |
|-------------------|-------------|---------|
| `SOURCE_A` | Path to Source A file (`.csv`/`.xlsx`) | required |
| `SOURCE_B` | Path to Source B file (`.csv`/`.xlsx`) | required |
| `-o, --output` | Report file path | `reconciliation_report.txt` |
| `-t, --tolerance` | Allowed absolute score difference | `0.0` |
| `-d, --duplicates` | How to collapse rows sharing a name (`sum`, `mean`, `last`, `first`, `max`, `min`) | `sum` |

### Duplicate / repeated names (automatic pivot)

If the same `Name` appears on multiple rows, the tool **collapses them to one
row per name before comparing** — by default it **sums** the scores (a
group-by-name pivot). This makes the comparison robust no matter how the
spreadsheet is shaped. Change the behavior with `-d`:

```bash
# Total each person's scores (default)
score-reconciler A.xlsx B.csv -d sum

# Keep only the last row for a repeated name (no totaling)
score-reconciler A.xlsx B.csv -d last
```

The report shows how many duplicate rows were collapsed in each source.

### Using different column names

If your files use headers other than `Name` / `TotalScore`, add the header
(lowercase, no spaces) to the alias sets near the top of
[src/score_reconciler/loader.py](src/score_reconciler/loader.py):

```python
_NAME_ALIASES = {"name", "fullname", "candidatename"}
_SCORE_ALIASES = {"totalscore", "score", "total"}
```

### Tests

```bash
python -m pip install -e ".[dev]"
pytest
```

### Build the standalone app yourself

Builds a self-contained bundle with PyInstaller (no Python needed by end users).
**PyInstaller cannot cross-compile** — build on the OS you want to target.

**Windows:**
```powershell
.\build_windows.ps1
# -> dist\score-reconciler-windows-<arch>.zip
```

**Mac:**
```bash
chmod +x build_macos.sh
./build_macos.sh
# -> dist/score-reconciler-darwin-<arch>.zip
```

Both scripts produce a ready-to-send zip in `dist/`.

**onedir vs onefile** (advanced):
- **onedir** (default) — a folder with the executable + libraries. Works under
  hardened corporate policies (Application Control / WDAC).
- **onefile** — a single portable executable that self-extracts to temp at
  launch; more convenient but some locked-down machines block it.
  ```bash
  python build_executable.py --mode onefile
  ```

### Automated builds (GitHub Actions)

Every push to `main` (or a manual run from the **Actions** tab →
**Run workflow**) builds all three platform zips in the cloud — no local
Mac/Windows hardware needed. Grab them from the run's **Artifacts** section.
Workflow: [.github/workflows/build.yml](.github/workflows/build.yml).


