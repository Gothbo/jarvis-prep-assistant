"""Helper script for start.bat: loads .env and writes env vars to a temp .bat file.

Usage::

    python _load_env.py

Reads ``.env`` via :func:`jarvis.config.load_config`, then writes the
relevant keys to ``%TEMP%\\jarvis_env.bat`` so that the calling batch
script can import them with a simple ``call``.
"""
import os
import sys
import tempfile

try:
    # Add src to path so jarvis.config is importable
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
    from jarvis.config import load_config

    load_config()

    out_path = os.path.join(tempfile.gettempdir(), "jarvis_env.bat")
    keys = [
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_TIMEOUT",
        "THREAT_INTEL_API_KEY",
        "JARVIS_PASSWORD",
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        for k in keys:
            v = os.environ.get(k, "")
            if v:
                f.write(f"set {k}={v}\n")

except Exception as e:
    print(f"[!] Warning: _load_env.py failed: {e}", file=sys.stderr)
    sys.exit(1)
