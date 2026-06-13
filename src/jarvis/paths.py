"""Project path utilities - resolve data directories correctly on any platform."""

import os
from pathlib import Path


def get_project_root() -> Path:
    """Resolve the project root directory.

    Works both in local dev (editable install) and on Streamlit Cloud
    (where the repo is cloned as-is and cwd is the project root).
    """
    # Strategy 1: relative to source tree (works in local dev)
    source_root = Path(__file__).resolve().parent.parent.parent
    if (source_root / "data" / "cases").exists():
        return source_root

    # Strategy 2: relative to cwd (works on Streamlit Cloud)
    cwd_root = Path.cwd()
    if (cwd_root / "data" / "cases").exists():
        return cwd_root

    # Strategy 3: walk up from __file__ looking for data/cases/
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "data" / "cases").exists():
            return current
        current = current.parent

    # Fallback: return source root even if data dir not found
    return source_root


# Pre-computed paths for convenience
DATA_DIR = get_project_root() / "data"
DICT_DIR = DATA_DIR / "dict"

# Cache dirs: prefer writable location on read-only filesystems (e.g. Streamlit Cloud)
_WRITABLE_ROOT = Path(os.environ.get("TMPDIR", "/tmp")) if not os.access(str(DATA_DIR), os.W_OK) else DATA_DIR
CACHE_DIR = _WRITABLE_ROOT / "jarvis_cache" if _WRITABLE_ROOT != DATA_DIR else DATA_DIR / "cache"
CHROMA_DIR = DATA_DIR / "chroma_db"
