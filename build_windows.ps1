# Build the Windows standalone executable (score-reconciler.exe).
# Run from the score-reconciler folder:  .\build_windows.ps1
$ErrorActionPreference = "Stop"
python -m pip install --upgrade pip
python -m pip install -e ".[build]"
python build_executable.py --mode onedir --zip
Write-Host "`nDone. Send the zip in .\dist\ (score-reconciler-windows-*.zip) to end users."
