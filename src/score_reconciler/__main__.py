"""Enable ``python -m score_reconciler`` and serve as the PyInstaller entry point."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
