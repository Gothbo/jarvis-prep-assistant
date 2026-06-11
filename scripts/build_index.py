"""Build or update the ChromaDB vector index."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jarvis.knowledge.loader import load_all
from jarvis.search.indexer import build_index


def main() -> int:
    print("Loading knowledge base...")
    kb = load_all()
    print(f"Loaded {len(kb.cases)} cases")

    print("Building vector index...")
    success = build_index(kb)

    if success:
        print("Index built successfully")
        return 0
    else:
        print("Index build failed - will use keyword fallback")
        return 1


if __name__ == "__main__":
    sys.exit(main())
