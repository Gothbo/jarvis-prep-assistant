"""Centralized configuration loader for JARVIS.

Loads environment variables from a ``.env`` file (if present) and provides
helper functions to access configuration values.  Tries ``python-dotenv``
first, then falls back to a built-in minimal parser.
"""

import logging
import os
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)

_LOADED = False


def _find_project_root() -> Path:
    """Locate the project root (the directory containing ``pyproject.toml``)."""
    # Relative to this source file: src/jarvis/config.py -> root is 3 levels up
    source_root = Path(__file__).resolve().parent.parent.parent
    if (source_root / "pyproject.toml").exists():
        return source_root

    # Relative to cwd
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists():
        return cwd

    # Walk up from __file__
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent

    return source_root


def _load_dotenv_fallback(path: Path) -> None:
    """Simple ``.env`` loader without the ``python-dotenv`` dependency.

    Only sets variables that are *not* already present in ``os.environ``
    so that real environment variables always take precedence.
    """
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError as exc:
        logger.debug("Could not read .env file: %s", exc)


def load_config() -> None:
    """Load environment configuration (idempotent -- safe to call multiple times).

    1. Tries ``python-dotenv`` if installed.
    2. Falls back to a built-in ``.env`` parser.
    3. Logs a warning when ``LLM_API_KEY`` is missing or still a placeholder.
    """
    global _LOADED  # noqa: PLW0603
    if _LOADED:
        return
    _LOADED = True

    root = _find_project_root()
    env_path = root / ".env"

    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        load_dotenv(dotenv_path=str(env_path), override=False)
    except ImportError:
        _load_dotenv_fallback(env_path)

    # Validate
    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        logger.warning(
            "LLM_API_KEY is not set. LLM-powered features will be unavailable."
        )
    elif api_key.startswith("sk-your") or "placeholder" in api_key.lower():
        warnings.warn(
            "LLM_API_KEY appears to be a placeholder. "
            "Set a real API key in .env or as an environment variable.",
            stacklevel=2,
        )


def get_config() -> dict[str, str]:
    """Return a summary of all configuration values with masked secrets.

    Safe to use in logs / debug output -- API keys are partially hidden.
    """
    def _mask(value: str) -> str:
        if len(value) <= 8:
            return "****"
        return value[:4] + "****" + value[-4:]

    keys = [
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_TIMEOUT",
        "THREAT_INTEL_API_KEY",
        "JARVIS_PASSWORD",
    ]
    result: dict[str, str] = {}
    for key in keys:
        value = os.environ.get(key, "")
        if not value:
            result[key] = "(not set)"
        elif "KEY" in key or "PASSWORD" in key:
            result[key] = _mask(value)
        else:
            result[key] = value
    return result
