"""Console entrypoint for `video2robot`.

This is intentionally a thin wrapper that delegates to the repository CLI scripts.
It exists so that `pip install -e .` can expose a stable console script.

Usage:
    video2robot --action "Action sequence: The subject walks forward."
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path

from .config import PROJECT_ROOT


def main() -> None:
    script_path = Path(PROJECT_ROOT) / "scripts" / "run_pipeline.py"
    if not script_path.exists():
        raise FileNotFoundError(f"run_pipeline.py not found: {script_path}")

    argv = [sys.executable, str(script_path), *sys.argv[1:]]
    raise SystemExit(subprocess.call(argv, cwd=str(PROJECT_ROOT)))
