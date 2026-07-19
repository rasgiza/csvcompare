#!/usr/bin/env bash
# Build the macOS standalone binary (score-reconciler).
# Run from the score-reconciler folder:  ./build_macos.sh
set -euo pipefail

python3 -m pip install --upgrade pip
python3 -m pip install -e ".[build]"
python3 build_executable.py --mode onedir --zip

echo ""
echo "Done. Send the zip in ./dist/ (score-reconciler-darwin-*.zip) to end users."
echo "On first run, macOS Gatekeeper may block an unsigned binary."
echo "Allow it with:  xattr -dr com.apple.quarantine ./score-reconciler"
