@echo off
REM ============================================================
REM  score-reconciler - Windows launcher
REM  Checks for Python, installs it via winget if missing,
REM  installs dependencies, then runs the comparison.
REM
REM  Usage:
REM    run_windows.bat "SourceA.csv" "SourceB.csv" -o report.txt
REM ============================================================
setlocal

REM --- 1. Find a Python interpreter (py launcher or python) ---
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
    where python >nul 2>nul && set "PYCMD=python"
)

REM --- 2. If none found, try to install Python via winget ---
if not defined PYCMD (
    echo Python was not found on this computer.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo.
        echo winget is not available, so Python cannot be installed automatically.
        echo Please install Python 3 from https://www.python.org/downloads/
        echo and be sure to check "Add Python to PATH" during setup, then run this again.
        echo.
        echo Alternatively, download the standalone app ^(no Python needed^) from:
        echo   https://github.com/rasgiza/csvcompare/actions
        pause
        exit /b 1
    )
    echo Installing Python 3.12 via winget. Please approve any prompts...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    echo.
    echo Python was installed. Please CLOSE this window and run run_windows.bat again
    echo so the new PATH takes effect.
    pause
    exit /b 0
)

echo Using Python command: %PYCMD%

REM --- 3. Install dependencies (quietly) ---
echo Installing dependencies...
%PYCMD% -m pip install --upgrade pip >nul 2>nul
%PYCMD% -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo Failed to install dependencies. See the messages above.
    pause
    exit /b 1
)

REM --- 4. Run the tool with whatever arguments were passed ---
echo.
echo Running score-reconciler...
%PYCMD% -m score_reconciler.cli %*
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
    echo DONE - no issues found.
) else if "%EXITCODE%"=="1" (
    echo DONE - issues were found. See the report file for details.
) else (
    echo There was an error. See the messages above.
)
pause
exit /b %EXITCODE%
