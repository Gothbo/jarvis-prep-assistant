"""Knowledge base loader - reads and validates YAML data files."""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from jarvis.models.case import Case
from jarvis.models.methodology import Methodology
from jarvis.models.product import Product
from jarvis.models.sensitivity import SensitivityProfile
from jarvis.paths import DATA_DIR

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Container for all loaded knowledge data."""

    def __init__(
        self,
        cases: list[Case],
        methodologies: list[Methodology],
        sensitivities: list[SensitivityProfile],
        products: list[Product],
    ):
        self.cases = cases
        self.methodologies = methodologies
        self.sensitivities = sensitivities
        self.products = products


def _load_yaml_files(directory: Path) -> list[dict[str, Any]]:
    """Load all YAML files from a directory, skipping invalid ones."""
    results = []
    if not directory.exists():
        raise FileNotFoundError(
            f"Knowledge data directory not found: {directory}"
        )

    for filepath in sorted(directory.glob("*.yaml")):
        try:
            with open(filepath, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                results.append(data)
        except (OSError, yaml.YAMLError) as e:
            logger.warning("Failed to load %s: %s", filepath.name, e)
        except Exception:
            logger.exception("Unexpected error loading %s", filepath.name)

    return results


@lru_cache(maxsize=1)
def load_cases(data_dir: Path | None = None) -> list[Case]:
    """Load and validate all case YAML files."""
    base = data_dir or DATA_DIR
    raw_list = _load_yaml_files(base / "cases")
    cases = []
    for raw in raw_list:
        try:
            cases.append(Case.model_validate(raw))
        except (ValidationError, ValueError, TypeError) as e:
            logger.warning("Invalid case data: %s", e)
        except Exception:
            logger.exception("Unexpected error validating case data")
    return cases


@lru_cache(maxsize=1)
def load_methodologies(data_dir: Path | None = None) -> list[Methodology]:
    """Load and validate all methodology YAML files."""
    base = data_dir or DATA_DIR
    raw_list = _load_yaml_files(base / "methodologies")
    methods = []
    for raw in raw_list:
        try:
            methods.append(Methodology.model_validate(raw))
        except (ValidationError, ValueError, TypeError) as e:
            logger.warning("Invalid methodology data: %s", e)
        except Exception:
            logger.exception("Unexpected error validating methodology data")
    return methods


@lru_cache(maxsize=1)
def load_sensitivities(data_dir: Path | None = None) -> list[SensitivityProfile]:
    """Load and validate all sensitivity profile YAML files."""
    base = data_dir or DATA_DIR
    raw_list = _load_yaml_files(base / "sensitivities")
    profiles = []
    for raw in raw_list:
        try:
            profiles.append(SensitivityProfile.model_validate(raw))
        except (ValidationError, ValueError, TypeError) as e:
            logger.warning("Invalid sensitivity data: %s", e)
        except Exception:
            logger.exception("Unexpected error validating sensitivity data")
    return profiles


@lru_cache(maxsize=1)
def load_products(data_dir: Path | None = None) -> list[Product]:
    """Load and validate all product YAML files."""
    base = data_dir or DATA_DIR
    raw_list = _load_yaml_files(base / "products")
    products = []
    for raw in raw_list:
        try:
            products.append(Product.model_validate(raw))
        except (ValidationError, ValueError, TypeError) as e:
            logger.warning("Invalid product data: %s", e)
        except Exception:
            logger.exception("Unexpected error validating product data")
    return products


@lru_cache(maxsize=1)
def load_all(data_dir: Path | None = None) -> KnowledgeBase:
    """Load all knowledge data into a unified KnowledgeBase object."""
    return KnowledgeBase(
        cases=load_cases(data_dir),
        methodologies=load_methodologies(data_dir),
        sensitivities=load_sensitivities(data_dir),
        products=load_products(data_dir),
    )
