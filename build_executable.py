#!/usr/bin/env python3
"""Cross-platform build script for the score-reconciler standalone executable.

Produces a self-contained build (no Python or pip needed on the target machine)
using PyInstaller. Run this ON the OS you want to target:

    Windows -> dist/score-reconciler/score-reconciler.exe  (onedir, default)
    macOS   -> dist/score-reconciler/score-reconciler       (Mach-O binary)
    Linux   -> dist/score-reconciler/score-reconciler       (ELF binary)

PyInstaller CANNOT cross-compile: build the Windows binary on Windows and the
macOS binary on a Mac.

Modes:
    --mode onedir  (default) A folder with the exe + libraries. Works under
                   locked-down Application Control / WDAC policies because it
                   does not extract a DLL to the temp folder at launch.
    --mode onefile A single portable exe/binary that self-extracts to temp at
                   launch. Most convenient, but hardened machines may block it.

Usage:
    pip install pyinstaller
    python build_executable.py            # onedir
    python build_executable.py --mode onefile
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "pyi_entry.py"
APP_NAME = "score-reconciler"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the score-reconciler executable.")
    parser.add_argument(
        "--mode",
        choices=["onefile", "onedir"],
        default="onedir",
        help=(
            "onedir (default): a folder with the exe + libs, works under locked-down "
            "Application Control / WDAC policies. onefile: a single portable exe that "
            "extracts to temp at launch (may be blocked on hardened machines)."
        ),
    )
    parser.add_argument(
        "--zip",
        dest="make_zip",
        action="store_true",
        help="After building, package the result into a ready-to-send zip in dist/.",
    )
    args = parser.parse_args(argv)

    system = platform.system()
    print(f"Building {APP_NAME} for {system} ({platform.machine()}) [{args.mode}]")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        f"--{args.mode}",
        "--clean",
        "--noconfirm",
        "--name",
        APP_NAME,
        # pandas/openpyxl pull data + hidden imports; let PyInstaller collect them.
        "--collect-submodules",
        "pandas",
        "--collect-submodules",
        "openpyxl",
        str(ENTRY),
    ]

    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("Build FAILED.", file=sys.stderr)
        return result.returncode

    suffix = ".exe" if system == "Windows" else ""
    if args.mode == "onefile":
        out = ROOT / "dist" / f"{APP_NAME}{suffix}"
        print(f"\nBuild complete: {out}")
        print("Distribute this single file to end users - no Python required.")
        package_root = out  # a single file
    else:
        folder = ROOT / "dist" / APP_NAME
        out = folder / f"{APP_NAME}{suffix}"
        print(f"\nBuild complete: {out}")
        print(f"Distribute the ENTIRE folder '{folder}' (zip it) - no Python required.")
        print("End users run the executable inside that folder.")
        package_root = folder  # a directory

    if args.make_zip:
        archive = _make_zip(package_root, system)
        print(f"\nPackaged for distribution: {archive}")
        print("Send this single zip to end users.")

    return 0


def _make_zip(package_root: Path, system: str) -> Path:
    """Zip the build output into dist/<name>-<os>-<arch>.zip."""
    arch = platform.machine().lower()
    os_tag = system.lower()
    base = ROOT / "dist" / f"{APP_NAME}-{os_tag}-{arch}"

    if package_root.is_dir():
        # Zip the folder, preserving the top-level folder name inside the archive.
        return Path(
            shutil.make_archive(
                str(base), "zip", root_dir=package_root.parent, base_dir=package_root.name
            )
        )
    # onefile: zip just the single binary.
    return Path(
        shutil.make_archive(
            str(base), "zip", root_dir=package_root.parent, base_dir=package_root.name
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
