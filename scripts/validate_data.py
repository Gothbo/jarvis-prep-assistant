"""Data validation script for YAML knowledge files."""

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jarvis.models.case import Case
from jarvis.models.methodology import Methodology
from jarvis.models.sensitivity import SensitivityProfile
from jarvis.models.product import Product

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

MODEL_MAP = {
    "cases": Case,
    "methodologies": Methodology,
    "sensitivities": SensitivityProfile,
    "products": Product,
}


def validate_file(filepath: Path, model_class) -> tuple[bool, str]:
    """Validate a single YAML file against its model."""
    try:
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return False, f"{filepath.name}: empty file"

        model_class.model_validate(data)
        return True, ""
    except ValidationError as e:
        return False, f"{filepath.name}: {e}"
    except yaml.YAMLError as e:
        return False, f"{filepath.name}: YAML parse error - {e}"
    except Exception as e:
        return False, f"{filepath.name}: {type(e).__name__} - {e}"


def check_duplicate_ids(data_dir: Path) -> list[str]:
    """Check for duplicate IDs across all YAML files."""
    all_ids: dict[str, str] = {}
    errors = []

    for subdir_name in MODEL_MAP:
        subdir = data_dir / subdir_name
        if not subdir.exists():
            continue

        for filepath in subdir.glob("*.yaml"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and "id" in data:
                    doc_id = data["id"]
                    if doc_id in all_ids:
                        errors.append(
                            f"Duplicate ID '{doc_id}' in {filepath.name} "
                            f"and {all_ids[doc_id]}"
                        )
                    else:
                        all_ids[doc_id] = filepath.name
            except Exception:
                pass

    return errors


def main() -> int:
    """Run all validations. Returns 0 on success, 1 on failure."""
    total = 0
    passed = 0
    errors = []

    # Check if data directory exists and has content
    has_data = False
    for subdir_name in MODEL_MAP:
        subdir = DATA_DIR / subdir_name
        if subdir.exists() and list(subdir.glob("*.yaml")):
            has_data = True
            break

    if not has_data:
        print("WARNING: Knowledge base is empty - no YAML files found in data/")
        return 1

    # Validate each file
    for subdir_name, model_class in MODEL_MAP.items():
        subdir = DATA_DIR / subdir_name
        if not subdir.exists():
            continue

        for filepath in sorted(subdir.glob("*.yaml")):
            total += 1
            ok, msg = validate_file(filepath, model_class)
            if ok:
                passed += 1
            else:
                errors.append(msg)

    # Check duplicates
    dup_errors = check_duplicate_ids(DATA_DIR)
    errors.extend(dup_errors)

    # Report
    if errors:
        print(f"FAILED: {passed}/{total} files passed")
        for err in errors:
            print(f"  ERROR: {err}")
        return 1

    print(f"All {total} files passed validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
