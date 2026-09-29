"""
paths.py - Locate the ML backend and the results folder, independent of the
current working directory or where the project was unzipped.

"""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

# Where analysis results (CSV) are stored. Always created, with parents.
RESULTS_DIR = APP_DIR / "backend"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

_REQUIRED = ("xgboost_model.json", "feature_extraction.py", "preprocessing.py")


def _is_backend(d: Path) -> bool:
    return d.is_dir() and all((d / f).exists() for f in _REQUIRED)


def find_backend_dir():
    """Return the backend directory as a Path, or None if it can't be found."""
    candidates = []
    env = os.environ.get("TRUTHLENS_BACKEND")
    if env:
        candidates.append(Path(env))
    candidates += [
        APP_DIR / "backend",
        APP_DIR.parent / "backend",
        APP_DIR.parent / "backend" / "backend_v3",
        APP_DIR.parent / "backend_v3",
        APP_DIR / "backend_v3",
    ]
    for c in candidates:
        if _is_backend(c):
            return c
    return None
