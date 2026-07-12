"""Shared pytest fixtures and helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


def load_vectors(chain: str) -> dict:
    """Load test vectors from tests/fixtures/<chain>_vectors.json."""
    path = FIXTURES_DIR / f"{chain}_vectors.json"
    if not path.exists():
        pytest.skip(f"missing fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
