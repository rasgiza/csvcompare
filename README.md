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

> **No Python required.** The downloaded app bundles everything it needs. You do
> **not** need to install Python, pip, or anything else to use it this way.

### Alternative: run from source with the Windows helper

If you'd rather run the Python source (not the bundled app) but don't have
Python installed, use the included launcher. Double-click or run it from a
terminal — it checks for Python, installs it via `winget` if missing, installs
dependencies, then runs the tool:

```bat
run_windows.bat "C:\path\to\SourceA.csv" "C:\path\to\SourceB.csv" -o "C:\path\to\report.txt"
```

(A Python script cannot install Python by itself, so this launcher `.bat` does
the bootstrap step for you. If `winget` is unavailable it points you to the
python.org installer or the no-Python bundled app above.)

---

## For developers

### Run from source

**Recommended (works everywhere, avoids old-pip errors) — use a virtual environment.**
Pick your operating system:

#### Windows (PowerShell)

```powershell
py --version                     # check Python is installed (e.g. 3.13)
# If that fails, install it:  winget install -e --id Python.Python.3.13
# then close and reopen the terminal.

git clone https://github.com/rasgiza/csvcompare.git
cd csvcompare

py -m venv .venv                 # create the virtual environment
.venv\Scripts\Activate.ps1       # activate it
py -m pip install --upgrade pip
pip install -e .
```

#### Mac / Linux (Terminal)

```bash
python3 --version                # check Python is installed
# If that fails on Mac:  brew install python

git clone https://github.com/rasgiza/csvcompare.git
cd csvcompare

python3 -m venv .venv            # create the virtual environment
source .venv/bin/activate        # activate it
python -m pip install --upgrade pip
pip install -e .
```

> **Why the venv?** A system Python often ships an old `pip` that can't do an
> editable (`-e`) install and can't write to site-packages, which produces
> errors like *"Directory cannot be installed in editable mode"* or
> *"site-packages is not writeable"*. A venv gives you a fresh, writable,
> upgradeable pip.

**No editable install needed?** Just install the dependencies and run the tool
(same on both platforms once the venv is active):

```bash
pip install -r requirements.txt          # runtime only (pandas, openpyxl)
# or, for tests + building the app too:
pip install -r requirements-dev.txt
```

(Dependencies are declared once in `pyproject.toml`; the `requirements*.txt`
files mirror them for a simpler, old-pip-friendly install.)

Generate sample data and try it:

**Windows (PowerShell):**
```powershell
py scripts\generate_sample_data.py
py -m score_reconciler.cli data\source_a.xlsx data\source_b.csv -o reconciliation_report.txt
```

**Mac / Linux:**
```bash
python3 scripts/generate_sample_data.py
python3 -m score_reconciler.cli data/source_a.xlsx data/source_b.csv -o reconciliation_report.txt
```

(After `pip install -e .` the shortcut `score-reconciler ...` also works inside
the activated venv on either platform.)

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
| `-d, --duplicates` | How to collapse rows sharing a name (`last`, `first`, `sum`, `mean`, `max`, `min`) | `last` |

### Duplicate / repeated names (automatic pivot)

If the same `Name` appears on multiple rows, the tool **collapses them to one
row per name before comparing**. By default it keeps a **single** row per name
(`last`) and takes the plain score difference — so a name listed twice with the
same score is treated as one entry, not doubled. Each source is collapsed
independently; the tool never pairs duplicate rows across the two files.

Change the behavior with `-d`:

```bash
# Default: keep one row per name, then compare the difference
score-reconciler A.xlsx B.csv -d last

# Opt-in: total each person's scores before comparing (group-by-sum)
score-reconciler A.xlsx B.csv -d sum
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


