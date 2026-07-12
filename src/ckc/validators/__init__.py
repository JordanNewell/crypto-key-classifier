"""Validator registry with auto-discovery.

Dropping a new validators/foo.py that subclasses Validator and exports
a class with a `chain` attribute automatically adds it to the pipeline.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Iterator

from ckc.validators.base import Validator


def _all_validator_classes() -> list[type[Validator]]:
    """Walk this package, find Validator subclasses, return them."""
    classes: list[type[Validator]] = []
    seen_names: set[str] = set()

    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name in {"base", "__init__"}:
            continue
        try:
            module = importlib.import_module(f"{__name__}.{module_info.name}")
        except ImportError:
            continue
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                hasattr(obj, "chain")
                and hasattr(obj, "formats")
                and hasattr(obj, "shape_match")
                and hasattr(obj, "validate")
                and obj.__module__ == module.__name__
                and obj.__name__ not in seen_names
            ):
                classes.append(obj)
                seen_names.add(obj.__name__)
    return classes


_REGISTRY: list[Validator] | None = None


def all_validators() -> list[Validator]:
    """Return instantiated validators (cached)."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = [cls() for cls in _all_validator_classes()]
    return _REGISTRY


def reset_registry() -> None:
    """For testing: force re-discovery on next call to all_validators()."""
    global _REGISTRY
    _REGISTRY = None
