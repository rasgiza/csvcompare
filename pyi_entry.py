"""PyInstaller entry point (uses an absolute import so it works when frozen)."""

from score_reconciler.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
