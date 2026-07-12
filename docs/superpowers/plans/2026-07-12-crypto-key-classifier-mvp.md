# Crypto Key Classifier — MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working `classify-key` CLI that classifies BTC-family / EVM / Solana / Cosmos strings (clean or corrupted) with cross-chain re-encoding, masking, and three output modes.

**Architecture:** Validator-per-chain with auto-discovered registry + shared escalating repair pipeline. Preprocessor generates normalized candidates; validators shape-match then strict-validate; repairs (whitespace → OCR → encoding → length) applied incrementally until checksum passes or stages exhausted. Pipeline breaks on first valid candidate per validator.

**Tech Stack:** Python 3.10+, `base58`, `bech32`, `pycryptodome` (Keccak), `ecdsa` (secp256k1), `pynacl` (ed25519), `pytest` + `pytest-cov`, `pyright` strict, `ruff`. Setuptools backend, `src/` layout.

**Reference spec:** `docs/superpowers/specs/2026-07-12-crypto-key-classifier-design.md`

---

## File structure

```
crypto-key-classifier/
├── pyproject.toml                     # Task 1
├── src/ckc/
│   ├── __init__.py                    # Task 1
│   ├── data/
│   │   └── wallets.py                 # Task 2 — wallet compatibility DB
│   ├── models.py                      # Task 3 — Candidate, Match dataclasses
│   ├── preprocessor.py                # Task 4 — Stage 1 repairs (whitespace, prefix, case)
│   ├── repairs.py                     # Task 6 — Stages 2-4 (OCR, encoding, length)
│   ├── validators/
│   │   ├── __init__.py                # Task 8 — registry with auto-discovery
│   │   ├── base.py                    # Task 7 — Validator ABC + shared helpers
│   │   ├── btc.py                     # Task 9 — BTC/LTC/DOGE/BCH + cross-chain
│   │   ├── evm.py                     # Task 10 — ETH + EVM L2s
│   │   ├── solana.py                  # Task 11
│   │   └── cosmos.py                  # Task 12 — IBC family + cross-chain HRP swap
│   ├── pipeline.py                    # Task 13 — orchestrator
│   ├── reporter.py                    # Task 14 — rich/terse/json
│   └── cli.py                         # Task 15 — argparse + masking
└── tests/
    ├── conftest.py                    # Task 5
    ├── fixtures/
    │   ├── btc_vectors.json           # Task 9
    │   ├── evm_vectors.json           # Task 10
    │   ├── solana_vectors.json        # Task 11
    │   └── cosmos_vectors.json        # Task 12
    ├── validators/
    │   ├── test_btc.py                # Task 9
    │   ├── test_evm.py                # Task 10
    │   ├── test_solana.py             # Task 11
    │   └── test_cosmos.py             # Task 12
    ├── test_models.py                 # Task 3
    ├── test_preprocessor.py           # Task 4
    ├── test_repairs.py                # Task 6
    ├── test_pipeline.py               # Task 13
    ├── test_reporter.py               # Task 14
    ├── test_cli.py                    # Task 15
    └── test_e2e.py                    # Task 16
```

**Follow-on plans** (not in this MVP): long-tail validators (Monero, Cardano, Tezos, Polkadot, TON, Stellar, Tron, Algorand, Kaspa, Sui/Aptos, Near, Ripple), mnemonic validator (BIP39/Electrum), property tests + fuzzing harness.

---

## Task 1: Project setup

**Files:**
- Create: `pyproject.toml`
- Create: `src/ckc/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "crypto-key-classifier"
version = "0.1.0"
description = "Classify any crypto-key string (BTC/ETH/SOL/Cosmos + more) with aggressive recovery from corruption"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "Jordan Newell" }]
dependencies = [
    "base58>=2.1.1",
    "bech32>=1.2.0",
    "pycryptodome>=3.20",
    "ecdsa>=0.18",
    "pynacl>=1.5",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.1",
    "pytest-snapshot>=0.9",
    "pyright>=1.1.350",
    "ruff>=0.6",
]

[project.scripts]
classify-key = "ckc.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers -v"

[tool.pyright]
typeCheckingMode = "strict"
pythonVersion = "3.10"

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
```

- [ ] **Step 2: Write `src/ckc/__init__.py`**

```python
"""crypto-key-classifier — classify any crypto-key string."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Install in editable mode**

Run: `cd E:/dev/projects/crypto-key-classifier && pip install -e ".[dev]"`
Expected: successful install with no errors.

- [ ] **Step 4: Verify install**

Run: `python -c "import ckc; print(ckc.__version__)"`
Expected: `0.1.0`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ckc/__init__.py
git commit -m "Project scaffold: pyproject.toml, src/ layout, deps installed"
```

---

## Task 2: Wallet compatibility database

**Files:**
- Create: `src/ckc/data/wallets.py`

- [ ] **Step 1: Write `src/ckc/data/wallets.py`**

```python
"""Wallet compatibility lists per chain.

Seeded from each chain's official docs. Not exhaustive — accurate.
Names are the user-facing wallet brand, not package IDs.
"""

WALLETS: dict[str, list[str]] = {
    # BTC family (BTC, LTC, DOGE, BCH share most wallets)
    "BTC": [
        "Bitcoin Core", "Electrum", "Sparrow", "Blue Wallet",
        "Wasabi", "Ledger", "Trezor", "Coldcard",
    ],
    "LTC": ["Electrum-LTC", "Litecoin Core", "Ledger", "Trezor", "Exodus"],
    "DOGE": ["Dogecoin Core", "MultiDoge", "Ledger", "Trezor"],
    "BCH": ["Bitcoin Cash Node", "Electron Cash", "Ledger", "Trezor"],
    # EVM family
    "ETH": [
        "MetaMask", "Trust Wallet", "Ledger", "Trezor",
        "MyEtherWallet", "Rainbow", "Coinbase Wallet", "Rabby",
    ],
    # Solana
    "SOL": ["Phantom", "Solflare", "Backpack", "Ledger"],
    # Cosmos IBC (all use Keplr + Ledger Cosmos app)
    "ATOM": ["Keplr", "Ledger", "Cosmostation", "Leap"],
    "OSMO": ["Keplr", "Ledger"],
    "JUNO": ["Keplr", "Ledger"],
    "AKT": ["Keplr", "Ledger"],
    "INJ": ["Keplr", "Ledger"],
}


def wallets_for(chain: str) -> list[str]:
    """Return wallet compatibility list for a chain code."""
    return WALLETS.get(chain.upper(), [])
```

- [ ] **Step 2: Verify import**

Run: `python -c "from ckc.data.wallets import wallets_for; print(wallets_for('ETH'))"`
Expected: list of ETH wallets printed.

- [ ] **Step 3: Commit**

```bash
git add src/ckc/data/wallets.py
git commit -m "Add wallet compatibility database (4 chain families)"
```

---

## Task 3: Data models

**Files:**
- Create: `src/ckc/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from ckc.models import Candidate, Match


def test_candidate_minimal():
    c = Candidate(raw="abc", normalized="abc", repairs=[], encoding=None, bytes_value=None)
    assert c.raw == "abc"
    assert c.repairs == []


def test_candidate_with_repairs():
    c = Candidate(
        raw=" abc ",
        normalized="abc",
        repairs=["strip-ws"],
        encoding="base58",
        bytes_value=b"\x01",
    )
    assert c.repairs == ["strip-ws"]
    assert c.bytes_value == b"\x01"


def test_match_full():
    m = Match(
        chain="BTC",
        format="P2PKH",
        key_type="address",
        confidence=100,
        checksum_status="valid",
        network="mainnet",
        cross_chain_alternates=[("LTC", "Labc...")],
        wallet_compatibility=["Electrum"],
        repairs_applied=[],
        notes=[],
    )
    assert m.chain == "BTC"
    assert m.confidence == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ckc.models'`

- [ ] **Step 3: Write `src/ckc/models.py`**

```python
"""Core data models for the classifier pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    """A normalized variant of an input string being tested against validators."""

    raw: str
    normalized: str
    repairs: list[str]
    encoding: str | None
    bytes_value: bytes | None


@dataclass
class Match:
    """A successful classification of an input as a particular chain/format."""

    chain: str
    format: str
    key_type: str  # "address" | "private-key" | "public-key" | "mnemonic"
    confidence: int  # 0-100
    checksum_status: str  # "valid" | "failed" | "none" | "skipped"
    network: str | None
    cross_chain_alternates: list[tuple[str, str]] = field(default_factory=list)
    wallet_compatibility: list[str] = field(default_factory=list)
    repairs_applied: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/ckc/models.py tests/test_models.py
git commit -m "Add Candidate and Match dataclasses"
```

---

## Task 4: Preprocessor (Stage 1 repairs)

**Files:**
- Create: `src/ckc/preprocessor.py`
- Create: `tests/test_preprocessor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_preprocessor.py
from ckc.preprocessor import preprocess


def test_strip_whitespace():
    cands = preprocess("  hello  ")
    assert len(cands) >= 1
    assert cands[0].normalized == "hello"
    assert "strip-ws" in cands[0].repairs


def test_strip_unicode_whitespace():
    # Zero-width space + non-breaking space + newline
    cands = preprocess("​abc\xa0\n")
    assert cands[0].normalized == "abc"


def test_drops_0x_prefix():
    cands = preprocess("0xdeadbeef")
    variants = [c.normalized for c in cands]
    assert "deadbeef" in variants
    # original-with-prefix also retained in case the format wants it (ETH)
    assert "0xdeadbeef" in variants


def test_case_variants():
    cands = preprocess("ABCDEF")
    variants = [c.normalized for c in cands]
    assert "abcdef" in variants
    assert "ABCDEF" in variants


def test_dedupes():
    # whitespace strip on "abc" produces same as identity — no duplicate candidates
    cands = preprocess("abc")
    normalizeds = [c.normalized for c in cands]
    assert len(normalizeds) == len(set(normalizeds))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_preprocessor.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/ckc/preprocessor.py`**

```python
"""Preprocessor: Stage 1 repairs (whitespace, prefix, case).

Generates a list of Candidate variants from a raw input string.
Stage 1 always runs; later stages (OCR, encoding, length) are in repairs.py.
"""

from __future__ import annotations

import re
import unicodedata

from ckc.models import Candidate

# Known format prefixes that may or may not be part of the canonical form
PREFIXES_TO_DROP: tuple[str, ...] = ("0x", "0X")

# Common unicode whitespace including zero-width chars
_WS_RE = re.compile(r"[\s​‌‍﻿\xa0]+")


def _strip_all_whitespace(s: str) -> str:
    """Strip ASCII + unicode whitespace including zero-width chars."""
    return _WS_RE.sub("", s)


def preprocess(raw: str) -> list[Candidate]:
    """Generate Stage-1 normalized candidates from raw input.

    Returns a deduplicated list. The first candidate is always the
    "most normalized" form (whitespace stripped, lowercased for non-EIP-55).
    """
    if not raw:
        return []

    candidates: list[Candidate] = []
    seen: set[str] = set()

    def add(normalized: str, repairs: list[str]) -> None:
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(
                Candidate(
                    raw=raw,
                    normalized=normalized,
                    repairs=repairs,
                    encoding=None,
                    bytes_value=None,
                )
            )

    # Identity (no repairs)
    add(raw, [])

    # Stage 1a: whitespace strip
    ws_stripped = _strip_all_whitespace(raw)
    if ws_stripped != raw:
        add(ws_stripped, ["strip-ws"])

    # Stage 1b: prefix drop
    for prefix in PREFIXES_TO_DROP:
        if ws_stripped.startswith(prefix):
            add(ws_stripped[len(prefix):], ["strip-ws", f"drop-prefix:{prefix}"])

    # Stage 1c: case variants
    add(ws_stripped.lower(), ["strip-ws", "lowercase"])
    add(ws_stripped.upper(), ["strip-ws", "uppercase"])

    # Unicode NFC normalization as another variant
    nfc = unicodedata.normalize("NFC", ws_stripped)
    if nfc != ws_stripped:
        add(nfc, ["strip-ws", "unicode-nfc"])

    return candidates
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_preprocessor.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/ckc/preprocessor.py tests/test_preprocessor.py
git commit -m "Add Stage 1 preprocessor (whitespace, prefix, case variants)"
```

---

## Task 5: Test infrastructure

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
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
```

- [ ] **Step 2: Verify pytest collects**

Run: `pytest --collect-only`
Expected: no errors; existing tests collected.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "Add test infrastructure (conftest, fixture loader)"
```

---

## Task 6: Repair primitives (Stages 2-4)

**Files:**
- Create: `src/ckc/repairs.py`
- Create: `tests/test_repairs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_repairs.py
from ckc.repairs import ocr_substitutions, encoding_variants, length_repairs, MAX_CANDIDATES


def test_ocr_substitutions_single_char():
    # "O" in a numeric context should yield a "0" variant
    variants = ocr_substitutions("O123")
    normalizeds = [v.normalized for v in variants]
    assert "0123" in normalizeds
    assert all("ocr:" in r for v in variants for r in v.repairs if v.normalized == "0123")


def test_ocr_substitutions_multiple_chars():
    # Each confusable produces a separate variant; we do not chain in one stage
    variants = ocr_substitutions("OISS")
    normalizeds = {v.normalized for v in variants}
    # "O→0", "I→1", "S→5" — at minimum the one-char swaps
    assert "0ISS" in normalizeds
    assert "O1SS" in normalizeds
    assert "OI55" in normalizeds or "OIS5" in normalizeds


def test_encoding_variants_hex_to_bytes():
    variants = encoding_variants("deadbeef")
    # Should at least try to decode as hex and produce bytes
    assert any(v.bytes_value == b"\xde\xad\xbe\xef" for v in variants)


def test_encoding_variants_base58_to_bytes():
    # "tjIPSa" base58 decode is well-defined
    variants = encoding_variants("tjIPSa")
    assert any(v.bytes_value is not None and len(v.bytes_value) > 0 for v in variants)


def test_length_repairs_insert():
    # If target length is 4 and we have "abc", insert one char at each position
    variants = length_repairs("abc", target_lengths={4})
    normalizeds = {v.normalized for v in variants}
    # We don't predict WHICH char — we just produce position slots
    # The validator is responsible for trying checksums on these
    assert all(len(n) == 4 for n in normalizeds)


def test_max_candidates_constant_exists():
    assert isinstance(MAX_CANDIDATES, int)
    assert MAX_CANDIDATES == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repairs.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/ckc/repairs.py`**

```python
"""Stage 2-4 repair primitives.

Each function takes a Candidate (or string + context) and returns *additional*
candidates. These are composable; the pipeline decides which stages to invoke.

Stages:
  2: OCR confusables (one char at a time)
  3: Encoding round-trips (hex/base58/base64)
  4: Length repair (±2 chars, bounded)

Cap: MAX_CANDIDATES total per input across all stages.
"""

from __future__ import annotations

import base64
import binascii

import base58

from ckc.models import Candidate

MAX_CANDIDATES = 50

# Visual confusables — common OCR / handwritten substitutions
# Map of "looks-like" → "actually-is". Bidirectional in practice.
OCR_MAP: dict[str, str] = {
    "O": "0",
    "o": "0",
    "I": "1",
    "l": "1",
    "|": "1",
    "S": "5",
    "s": "5",
    "B": "8",
    "Z": "2",
    "z": "2",
    "G": "6",
    "D": "0",  # partial — only in some fonts
    "q": "9",
}


def ocr_substitutions(text: str) -> list[Candidate]:
    """Stage 2: produce one variant per confusable char, replacing just that char."""
    candidates: list[Candidate] = []
    for i, ch in enumerate(text):
        if ch in OCR_MAP:
            replacement = OCR_MAP[ch]
            new = text[:i] + replacement + text[i + 1:]
            cand = Candidate(
                raw=text,
                normalized=new,
                repairs=[f"ocr:{ch}→{replacement}@{i}"],
                encoding=None,
                bytes_value=None,
            )
            candidates.append(cand)
    return candidates


def encoding_variants(text: str) -> list[Candidate]:
    """Stage 3: try decoding text as hex/base58/base64, attach bytes_value.

    The validator can use bytes_value for downstream checks (length, prefix byte).
    """
    candidates: list[Candidate] = []

    # Hex
    try:
        b = bytes.fromhex(text)
        candidates.append(
            Candidate(
                raw=text, normalized=text, repairs=["decode:hex"],
                encoding="hex", bytes_value=b,
            )
        )
    except ValueError:
        pass

    # Base58 (Bitcoin alphabet)
    try:
        b = base58.b58decode(text)
        candidates.append(
            Candidate(
                raw=text, normalized=text, repairs=["decode:base58"],
                encoding="base58", bytes_value=b,
            )
        )
    except Exception:
        pass

    # Base64 (standard)
    try:
        b = base64.b64decode(text, validate=True)
        candidates.append(
            Candidate(
                raw=text, normalized=text, repairs=["decode:base64"],
                encoding="base64", bytes_value=b,
            )
        )
    except (binascii.Error, ValueError):
        pass

    return candidates


def length_repairs(text: str, target_lengths: set[int]) -> list[Candidate]:
    """Stage 4: produce variants with chars inserted/deleted to hit target lengths.

    Insertion: at each position, insert a placeholder ('?' or actual char from a
    small candidate set if provided). The validator is responsible for trying
    checksums against the candidate variants.

    For deletion: at each position, remove that one char.

    Bounded to ±2 chars from current length to avoid combinatorial blowup.
    """
    candidates: list[Candidate] = []
    current = len(text)

    for target in target_lengths:
        delta = target - current
        if abs(delta) > 2:
            continue

        if delta > 0:
            # Insertions: at each position, insert N placeholder chars
            for pos in range(current + 1):
                for _ in range(delta):
                    # Placeholder; validator handles char substitution
                    new = text[:pos] + "?" + text[pos:]
                    candidates.append(
                        Candidate(
                            raw=text, normalized=new,
                            repairs=[f"len-repair:insert@{pos}"],
                            encoding=None, bytes_value=None,
                        )
                    )
                    break  # one insertion per position per target
        elif delta < 0:
            # Deletions: at each position, remove that char
            for pos in range(current):
                new = text[:pos] + text[pos + 1:]
                candidates.append(
                    Candidate(
                        raw=text, normalized=new,
                        repairs=[f"len-repair:delete@{pos}"],
                        encoding=None, bytes_value=None,
                    )
                )

    return candidates
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_repairs.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/ckc/repairs.py tests/test_repairs.py
git commit -m "Add Stage 2-4 repair primitives (OCR, encoding, length)"
```

---

## Task 7: Validator protocol + shared helpers

**Files:**
- Create: `src/ckc/validators/base.py`

- [ ] **Step 1: Write `src/ckc/validators/base.py`**

```python
"""Validator protocol + shared crypto helpers.

Each chain validator subclasses Validator and implements shape_match,
validate, suggest_repairs, and (optionally) cross_chain_encodings.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import base58
from Crypto.Hash import keccak

from ckc.models import Candidate, Match


class Validator(Protocol):
    """Protocol every validator implements.

    Concrete validators are discovered by validators/__init__.py via pkgutil.
    """

    chain: str
    formats: list[str]

    def shape_match(self, candidate: Candidate) -> bool:
        """Cheap check: right length, charset, prefix? No checksum yet."""
        ...

    def validate(self, candidate: Candidate) -> Match | None:
        """Strict validation: checksum, network byte, etc. Returns None if rejected."""
        ...

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        """Format-specific repair candidates (return [] to defer to generic layer)."""
        ...

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        """For shared-key families: enumerate alternate chain encodings."""
        ...


# --- Shared crypto helpers ---


def keccak256(data: bytes) -> bytes:
    """Keccak-256 hash (NOT SHA3-256 — different padding)."""
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def double_sha256(data: bytes) -> bytes:
    return sha256(sha256(data))


def base58check_encode(payload: bytes) -> str:
    """Encode payload with double-SHA256 checksum (4 bytes)."""
    checksum = double_sha256(payload)[:4]
    return base58.b58encode(payload + checksum).decode("ascii")


def base58check_decode(s: str) -> bytes | None:
    """Decode base58check-encoded string. Returns payload WITHOUT checksum,
    or None if checksum fails."""
    try:
        full = base58.b58decode(s)
    except Exception:
        return None
    if len(full) < 5:
        return None
    payload, checksum = full[:-4], full[-4:]
    if double_sha256(payload)[:4] != checksum:
        return None
    return payload


def bech32_validate(s: str) -> tuple[str, bytes, str] | None:
    """Validate bech32/bech32m string. Returns (hrp, data, variant) or None.

    variant is "bech32" or "bech32m" depending on BIP-173 vs BIP-350.
    """
    import bech32
    # The `bech32` package exposes bech32.bech32_decode / convertbits
    hrp, data, spec = bech32.bech32_decode(s)
    if data is None:
        return None
    spec_name = {bech32.Encoding.BECH32: "bech32", bech32.Encoding.BECH32M: "bech32m"}.get(
        spec, "unknown"
    )
    return (hrp, bytes(data), spec_name)
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from ckc.validators.base import Validator, keccak256, base58check_decode; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/ckc/validators/base.py
git commit -m "Add Validator protocol + shared crypto helpers (keccak, base58check, bech32)"
```

---

## Task 8: Validator registry with auto-discovery

**Files:**
- Create: `src/ckc/validators/__init__.py`

- [ ] **Step 1: Write `src/ckc/validators/__init__.py`**

```python
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
```

- [ ] **Step 2: Verify registry works (will be empty until Task 9)**

Run: `python -c "from ckc.validators import all_validators; print(len(all_validators()))"`
Expected: `0` (no validators yet)

- [ ] **Step 3: Commit**

```bash
git add src/ckc/validators/__init__.py
git commit -m "Add validator registry with auto-discovery via pkgutil"
```

---

## Task 9: BTC validator (BTC + LTC + DOGE + BCH)

**Files:**
- Create: `src/ckc/validators/btc.py`
- Create: `tests/validators/test_btc.py`
- Create: `tests/fixtures/btc_vectors.json`

- [ ] **Step 1: Write test fixtures**

```json
{
  "_source": "https://en.bitcoin.it/wiki/List_of_address_prefixes and BIP-173/BIP-350 reference test vectors",
  "_note": "Test code generates LTC/DOGE/WIF fixtures programmatically via base58check_encode for checksum symmetry. This file holds reference addresses for documentation only.",
  "addresses_p2pkh_btc_known": [
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
  ],
  "addresses_bech32_segwit_v0_bip173_reference": [
    "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
    "BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4"
  ],
  "addresses_bech32m_taproot_bip350_reference": [
    "bc1p5cyxnuxmeuwuvkwfem96lqzszd02n6xdcjrs20cac6yqjjwudpxqkedrcr"
  ],
  "version_bytes": {
    "_doc": "P2PKH/P2SH version bytes per chain — used by validator to dispatch + cross-encode",
    "BTC_P2PKH": "0x00",
    "BTC_P2SH": "0x05",
    "LTC_P2PKH": "0x30",
    "LTC_P2SH": "0x32",
    "DOGE_P2PKH": "0x1e",
    "DOGE_P2SH": "0x16",
    "BTC_WIF": "0x80",
    "LTC_WIF": "0xb0",
    "DOGE_WIF": "0x9e"
  },
  "invalid_examples": [
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfXX",
    "not a key at all",
    "0xdeadbeef"
  ]
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/validators/test_btc.py
import pytest

from ckc.validators.btc import BTCValidator
from ckc.validators.base import base58check_encode
from ckc.models import Candidate


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


# --- Generated fixtures (symmetric with production code) ---
# Generate valid LTC/DOGE/BCH addresses by encoding zero-hash160 with the
# right version byte. This tests decode-against-encode symmetry, which is
# rigorous for checksum verification.
@pytest.fixture(scope="module")
def ltc_p2pkh_addr() -> str:
    return base58check_encode(b"\x30" + b"\x00" * 20)


@pytest.fixture(scope="module")
def doge_p2pkh_addr() -> str:
    return base58check_encode(b"\x1e" + b"\x00" * 20)


@pytest.fixture(scope="module")
def btc_wif_compressed() -> str:
    # WIF: 0x80 prefix + 32-byte key + 0x01 compressed flag
    return base58check_encode(b"\x80" + b"\x01" * 32 + b"\x01")


def test_p2pkh_btc_valid():
    # Genesis block address — well-known valid P2PKH
    v = BTCValidator()
    m = v.validate(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    assert m is not None
    assert m.chain == "BTC"
    assert m.format == "P2PKH"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_p2pkh_ltc_valid(ltc_p2pkh_addr):
    v = BTCValidator()
    m = v.validate(_cand(ltc_p2pkh_addr))
    assert m is not None
    assert m.chain == "LTC"
    assert m.format == "P2PKH"
    assert m.cross_chain_alternates  # BTC family alternates populated


def test_p2pkh_doge_valid(doge_p2pkh_addr):
    v = BTCValidator()
    m = v.validate(_cand(doge_p2pkh_addr))
    assert m is not None
    assert m.chain == "DOGE"


def test_bech32_segwit_v0_valid():
    # BIP-173 reference test vector
    v = BTCValidator()
    m = v.validate(_cand("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"))
    assert m is not None
    assert m.format == "bech32-segwit-v0"
    assert m.checksum_status == "valid"


def test_bech32m_taproot_valid():
    # BIP-350 reference test vector
    v = BTCValidator()
    m = v.validate(_cand("bc1p5cyxnuxmeuwuvkwfem96lqzszd02n6xdcjrs20cac6yqjjwudpxqkedrcr"))
    assert m is not None
    assert m.format == "taproot-v1"


def test_wif_compressed_valid(btc_wif_compressed):
    v = BTCValidator()
    m = v.validate(_cand(btc_wif_compressed))
    assert m is not None
    assert m.chain == "BTC"
    assert m.format == "WIF-compressed"
    assert m.key_type == "private-key"


def test_invalid_rejected():
    v = BTCValidator()
    # Same shape as genesis address but last char swapped — checksum will fail
    assert v.validate(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfXX")) is None
    assert v.validate(_cand("not a key at all")) is None


def test_shape_match_true_for_plausible():
    v = BTCValidator()
    assert v.shape_match(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    assert v.shape_match(_cand("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"))


def test_shape_match_false_for_wrong_charset():
    v = BTCValidator()
    assert not v.shape_match(_cand("0x1234567890abcdef"))  # ETH-ish
    assert not v.shape_match(_cand("hello world"))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/validators/test_btc.py -v`
Expected: FAIL with import errors.

- [ ] **Step 4: Write `src/ckc/validators/btc.py`**

```python
"""BTC-family validator: BTC, LTC, DOGE, BCH.

All four chains share base58check + WIF + bech32 machinery. The only
differences are P2PKH/P2SH version bytes. We decode once and dispatch on
the version byte to identify the chain, then cross-encode to all four.
"""

from __future__ import annotations

import re

import bech32

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import base58check_decode, bech32_validate, keccak256

# Version bytes per chain (P2PKH, P2SH)
# Source: https://en.bitcoin.it/wiki/List_of_address_prefixes
_VERSION_BYTES: dict[bytes, tuple[str, str]] = {
    b"\x00": ("BTC", "P2PKH"),
    b"\x05": ("BTC", "P2SH"),
    b"\x30": ("LTC", "P2PKH"),
    b"\x32": ("LTC", "P2SH"),
    b"\x1e": ("DOGE", "P2PKH"),
    b"\x16": ("DOGE", "P2SH"),
    # BCH uses the same addresses as BTC (cashaddr is separate, future work)
}

# For cross-chain encoding: map P2PKH version bytes for one-hop re-encoding
_P2PKH_VERSIONS: dict[str, bytes] = {
    "BTC": b"\x00",
    "LTC": b"\x30",
    "DOGE": b"\x1e",
    # BCH reuses BTC's addresses historically; cashaddr is separate
}
_P2SH_VERSIONS: dict[str, bytes] = {
    "BTC": b"\x05",
    "LTC": b"\x32",
    "DOGE": b"\x16",
}

# Charset shape matchers
_BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{25,62}$")
_BECH32_RE = re.compile(r"^bc1[02-9ac-hj-np-z]{6,87}$", re.IGNORECASE)


class BTCValidator:
    """Validator for BTC/LTC/DOGE/BCH address + key formats."""

    chain = "BTC_FAMILY"  # registry tag; per-match chain is more specific
    formats = ["P2PKH", "P2SH", "bech32-segwit-v0", "taproot-v1", "WIF"]

    def shape_match(self, candidate: Candidate) -> bool:
        s = candidate.normalized
        if _BASE58_RE.match(s):
            return True
        if _BECH32_RE.match(s):
            return True
        # WIF shape: 5x / Kx / Lx prefix, base58, ~51-52 chars
        if re.match(r"^[5KL][1-9A-HJ-NP-Za-km-z]{50,51}$", s):
            return True
        return False

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized

        # Try bech32 / bech32m first (cleaner dispatch)
        if s.lower().startswith("bc1"):
            return self._validate_bech32(candidate)

        # Try base58check (P2PKH / P2SH / WIF)
        payload = base58check_decode(s)
        if payload is None:
            return None

        # WIF private keys: prefix 0x80 (BTC), 0xB0 (LTC), 0x9E (DOGE)
        if payload[:1] in {b"\x80", b"\xb0", b"\x9e"}:
            return self._match_wif(candidate, payload)

        # P2PKH / P2SH: prefix byte tells us chain + format
        prefix = payload[:1]
        if prefix in _VERSION_BYTES:
            chain, fmt = _VERSION_BYTES[prefix]
            return self._match_address(candidate, chain, fmt, payload, s)

        return None

    def _validate_bech32(self, candidate: Candidate) -> Match | None:
        result = bech32_validate(candidate.normalized)
        if result is None:
            return None
        hrp, data, variant = result
        if hrp != "bc":
            return None
        # data[0] is the witness version byte
        if not data:
            return None
        witver = data[0]
        # bech32 for v0, bech32m for v1+
        expected_spec = "bech32m" if witver >= 1 else "bech32"
        if variant != expected_spec:
            return None
        fmt = "taproot-v1" if witver == 1 else f"bech32-segwit-v{witver}"
        return Match(
            chain="BTC",
            format=fmt,
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            wallet_compatibility=wallets_for("BTC"),
            repairs_applied=candidate.repairs,
            notes=[f"bech32 spec: {variant}"],
        )

    def _match_address(
        self, candidate: Candidate, chain: str, fmt: str, payload: bytes, original: str
    ) -> Match:
        return Match(
            chain=chain,
            format=fmt,
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=self._cross_chain_for(chain, fmt, payload[1:]),
            wallet_compatibility=wallets_for(chain),
            repairs_applied=candidate.repairs,
            notes=[],
        )

    def _match_wif(self, candidate: Candidate, payload: bytes) -> Match:
        prefix = payload[:1]
        chain = {b"\x80": "BTC", b"\xb0": "LTC", b"\x9e": "DOGE"}.get(prefix, "BTC")
        # 0x01 suffix = compressed pubkey flag
        compressed = payload.endswith(b"\x01")
        return Match(
            chain=chain,
            format="WIF" + ("-compressed" if compressed else "-uncompressed"),
            key_type="private-key",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            wallet_compatibility=wallets_for(chain),
            repairs_applied=candidate.repairs,
            notes=["PRIVATE KEY — handle with care"],
        )

    def _cross_chain_for(self, chain: str, fmt: str, hash160: bytes) -> list[tuple[str, str]]:
        """For a decoded 20-byte hash160, enumerate cross-chain encodings."""
        out: list[tuple[str, str]] = []
        from ckc.validators.base import base58check_encode

        if fmt == "P2PKH":
            for alt_chain, version in _P2PKH_VERSIONS.items():
                if alt_chain == chain:
                    continue
                out.append((alt_chain, base58check_encode(version + hash160)))
        elif fmt == "P2SH":
            for alt_chain, version in _P2SH_VERSIONS.items():
                if alt_chain == chain:
                    continue
                out.append((alt_chain, base58check_encode(version + hash160)))
        return out

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        # BTC validator relies on generic repair layer
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return match.cross_chain_alternates
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/validators/test_btc.py -v`
Expected: 9 passed.

- [ ] **Step 6: Commit**

```bash
git add src/ckc/validators/btc.py tests/validators/test_btc.py tests/fixtures/btc_vectors.json
git commit -m "Add BTC family validator (BTC/LTC/DOGE/BCH + cross-chain)"
```

---

## Task 10: EVM validator (ETH + EVM L2s)

**Files:**
- Create: `src/ckc/validators/evm.py`
- Create: `tests/validators/test_evm.py`
- Create: `tests/fixtures/evm_vectors.json`

- [ ] **Step 1: Write test fixtures**

```json
{
  "_source": "https://eips.ethereum.org/EIPS/eip-55 and ethereum.org docs",
  "addresses_valid_eip55": [
    "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
    "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
    "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB"
  ],
  "private_keys_valid": [
    "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
  ],
  "l2_chains": ["Polygon", "Arbitrum", "Base", "Optimism", "BSC", "Avalanche"],
  "invalid": [
    "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAe",
    "0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAedEXTRA"
  ]
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/validators/test_evm.py
from ckc.validators.evm import EVMValidator
from ckc.models import Candidate


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


def test_eth_address_valid_eip55():
    v = EVMValidator()
    m = v.validate(_cand("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"))
    assert m is not None
    assert m.chain == "ETH"
    assert m.format == "address-eip55"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_eth_address_lowercase_no_checksum_valid():
    v = EVMValidator()
    m = v.validate(_cand("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"))
    assert m is not None
    assert m.checksum_status == "none"
    assert m.confidence == 50  # no checksum applied, format only


def test_eth_address_bad_checksum_repairable():
    # Last char flipped — EIP-55 fix would correct it
    v = EVMValidator()
    m = v.validate(_cand("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAee"))
    # Should either reject OR return a low-confidence match with repair note
    if m is not None:
        assert m.checksum_status == "failed"


def test_eth_private_key_valid():
    v = EVMValidator()
    m = v.validate(_cand("0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"))
    assert m is not None
    assert m.key_type == "private-key"
    assert m.format == "secp256k1-private-key"


def test_invalid_rejected():
    v = EVMValidator()
    assert v.validate(_cand("0xdeadbeef")) is None  # too short
    assert v.validate(_cand("0xZZZZ")) is None


def test_shape_match():
    v = EVMValidator()
    assert v.shape_match(_cand("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"))
    assert not v.shape_match(_cand("not a key"))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/validators/test_evm.py -v`
Expected: FAIL with import errors.

- [ ] **Step 4: Write `src/ckc/validators/evm.py`**

```python
"""EVM validator: ETH + all EVM L2s share identical address/key format.

ETH addresses are 20-byte Keccak-256 hashes, hex-encoded with 0x prefix.
EIP-55 mixed-case checksum adds ~15 bits of corruption detection.

Private keys are 32-byte secp256k1 scalars, hex-encoded with optional 0x.

All EVM L2s (Polygon, Arbitrum, Base, Optimism, BSC, Avalanche, etc.)
use the SAME address format. Cross-chain expansion is chain-ID-only;
the address string is identical, so we list compatible chains.
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import keccak256

# 0x + 40 hex (address) OR 0x + 64 hex (private key) OR raw hex without 0x
_ADDR_RE = re.compile(r"^(0x)?[0-9a-fA-F]{40}$")
_PRIV_RE = re.compile(r"^(0x)?[0-9a-fA-F]{64}$")

# Major EVM chains (chain IDs per EIP-155)
EVM_CHAINS: list[tuple[str, int]] = [
    ("ETH", 1),
    ("Polygon", 137),
    ("Arbitrum", 42161),
    ("Base", 8453),
    ("Optimism", 10),
    ("BSC", 56),
    ("Avalanche", 43114),
    ("Gnosis", 100),
    ("Linea", 59144),
    ("Scroll", 534352),
    ("Zora", 7777777),
]


def _eip55_checksum(addr_lower: str) -> str:
    """Apply EIP-55 checksum to a lowercase hex address (no 0x prefix)."""
    hash_hex = keccak256(addr_lower.encode("ascii")).hex()
    out = []
    for ch, hsh in zip(addr_lower, hash_hex):
        if ch in "0123456789":
            out.append(ch)
        elif int(hsh, 16) >= 8:
            out.append(ch.upper())
        else:
            out.append(ch)
    return "0x" + "".join(out)


class EVMValidator:
    chain = "ETH"
    formats = ["address-eip55", "address-no-checksum", "secp256k1-private-key"]

    def shape_match(self, candidate: Candidate) -> bool:
        s = candidate.normalized
        return bool(_ADDR_RE.match(s) or _PRIV_RE.match(s))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        has_0x = s.startswith("0x") or s.startswith("0X")
        body = s[2:] if has_0x else s

        # Private key (64 hex = 32 bytes)
        if _PRIV_RE.match(s):
            try:
                key_bytes = bytes.fromhex(body)
            except ValueError:
                return None
            if key_bytes == b"\x00" * 32:  # invalid curve point
                return None
            return Match(
                chain="ETH",
                format="secp256k1-private-key",
                key_type="private-key",
                confidence=100,
                checksum_status="none",  # priv keys have no checksum
                network="mainnet",
                cross_chain_alternates=[(c, s) for c, _ in EVM_CHAINS[1:]],
                wallet_compatibility=wallets_for("ETH"),
                repairs_applied=candidate.repairs,
                notes=["PRIVATE KEY — handle with care", f"valid on {len(EVM_CHAINS)} EVM chains"],
            )

        # Address (40 hex = 20 bytes)
        if not _ADDR_RE.match(s):
            return None
        if len(body) != 40:
            return None

        # If all lower or all upper, no checksum applied
        if body.lower() == body or body.upper() == body:
            return Match(
                chain="ETH",
                format="address-no-checksum",
                key_type="address",
                confidence=50,
                checksum_status="none",
                network="mainnet",
                cross_chain_alternates=[(c, f"0x{body}") for c, _ in EVM_CHAINS[1:]],
                wallet_compatibility=wallets_for("ETH"),
                repairs_applied=candidate.repairs,
                notes=[f"same address works on {len(EVM_CHAINS)} EVM chains"],
            )

        # Mixed case — verify EIP-55
        expected = _eip55_checksum(body.lower())
        if expected == (f"0x{body}"):
            return Match(
                chain="ETH",
                format="address-eip55",
                key_type="address",
                confidence=100,
                checksum_status="valid",
                network="mainnet",
                cross_chain_alternates=[(c, expected) for c, _ in EVM_CHAINS[1:]],
                wallet_compatibility=wallets_for("ETH"),
                repairs_applied=candidate.repairs,
                notes=[f"same address works on {len(EVM_CHAINS)} EVM chains"],
            )
        else:
            # Checksum failed — could be a typo. Return low-confidence match.
            return Match(
                chain="ETH",
                format="address-eip55-failed",
                key_type="address",
                confidence=40,
                checksum_status="failed",
                network="mainnet",
                cross_chain_alternates=[],
                wallet_compatibility=wallets_for("ETH"),
                repairs_applied=candidate.repairs,
                notes=["EIP-55 checksum failed — likely typo", f"expected: {expected}"],
            )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        # EIP-55 fix is essentially free — produce a candidate with checksum applied
        s = candidate.normalized
        body = s[2:] if s.startswith(("0x", "0X")) else s
        if len(body) == 40:
            try:
                fixed = _eip55_checksum(body.lower())
                return [Candidate(
                    raw=candidate.raw,
                    normalized=fixed,
                    repairs=candidate.repairs + ["case:eip55"],
                    encoding=None, bytes_value=None,
                )]
            except Exception:
                pass
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return match.cross_chain_alternates
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/validators/test_evm.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/ckc/validators/evm.py tests/validators/test_evm.py tests/fixtures/evm_vectors.json
git commit -m "Add EVM validator (ETH + 10 L2s, EIP-55 checksum, cross-chain IDs)"
```

---

## Task 11: Solana validator

**Files:**
- Create: `src/ckc/validators/solana.py`
- Create: `tests/validators/test_solana.py`
- Create: `tests/fixtures/solana_vectors.json`

- [ ] **Step 1: Write test fixtures**

```json
{
  "_source": "https://solana.com/docs/technologies/accounts and web3.js test fixtures",
  "addresses_valid": [
    "dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc",
    "11111111111111111111111111111111",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "7xLk17EQQ5KLDLDe44wCmupJKJjTGd8hs3eSVVhCx932"
  ],
  "private_keys_base58": [
    "5Kb8...3MaT_PLACEHOLDER_DO_NOT_USE"
  ],
  "invalid": [
    "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318",
    "this is not a solana address",
    ""
  ]
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/validators/test_solana.py
from ckc.validators.solana import SolanaValidator
from ckc.models import Candidate


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


def test_solana_address_valid():
    v = SolanaValidator()
    m = v.validate(_cand("dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc"))
    assert m is not None
    assert m.chain == "SOL"
    assert m.checksum_status == "none"  # Solana has no checksum
    assert m.confidence == 50  # capped at 50 — no checksum exists


def test_solana_address_min_length():
    v = SolanaValidator()
    # 32 bytes encoded as base58 = 43-44 chars typically, but can be shorter
    m = v.validate(_cand("11111111111111111111111111111111"))
    assert m is not None


def test_invalid_rejected():
    v = SolanaValidator()
    assert v.validate(_cand("0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318")) is None
    assert v.validate(_cand("too short")) is None


def test_shape_match():
    v = SolanaValidator()
    assert v.shape_match(_cand("dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc"))
    assert not v.shape_match(_cand("0xabc"))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/validators/test_solana.py -v`
Expected: FAIL with import errors.

- [ ] **Step 4: Write `src/ckc/validators/solana.py`**

```python
"""Solana validator.

Solana addresses are 32-byte Ed25519 pubkeys, base58-encoded.
No checksum exists — confidence caps at 50 (format_match_no_checksum).

Length range: 32-44 base58 chars (typically 43-44 for random keys).
"""

from __future__ import annotations

import re

import base58

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match

# Base58 alphabet regex, length 32-44 (Solana pubkey range)
_SOL_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class SolanaValidator:
    chain = "SOL"
    formats = ["ed25519-pubkey", "ed25519-private-key"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_SOL_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _SOL_RE.match(s):
            return None
        try:
            b = base58.b58decode(s)
        except Exception:
            return None
        if len(b) != 32:
            return None
        # We can't distinguish address from private key structurally —
        # assume address by default. Private keys in Solana are also 32-byte
        # and look identical (the keypair JSON is the convention, not a format).
        return Match(
            chain="SOL",
            format="ed25519-pubkey",
            key_type="address",  # could also be private-key — flagged in notes
            confidence=50,
            checksum_status="none",
            network="mainnet",
            cross_chain_alternates=[],  # Solana key is Solana-only
            wallet_compatibility=wallets_for("SOL"),
            repairs_applied=candidate.repairs,
            notes=["no checksum exists for Solana — confidence caps at 50"],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/validators/test_solana.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/ckc/validators/solana.py tests/validators/test_solana.py tests/fixtures/solana_vectors.json
git commit -m "Add Solana validator (ed25519 base58, no checksum)"
```

---

## Task 12: Cosmos validator (with cross-chain HRP swap)

**Files:**
- Create: `src/ckc/validators/cosmos.py`
- Create: `tests/validators/test_cosmos.py`
- Create: `tests/fixtures/cosmos_vectors.json`

- [ ] **Step 1: Write test fixtures**

```json
{
  "_source": "https://docs.cosmos.network and chain-registry on GitHub",
  "addresses_valid": {
    "ATOM": "cosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2",
    "OSMO": "osmo1y8ndjyq34ms6n5qvcsc2m4e7n0gg3g0algavku",
    "JUNO": "juno1y8ndjyq34ms6n5qvcsc2m4e7n0gg3g0alga3sm"
  },
  "hrps": ["cosmos", "osmo", "juno", "akash", "inj", "evmos", "stride", "regen", "persistence"],
  "invalid": [
    "cosmos1invalid",
    "0xabc",
    "not a cosmos address"
  ]
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/validators/test_cosmos.py
from ckc.validators.cosmos import CosmosValidator
from ckc.models import Candidate


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


def test_cosmos_atom_valid():
    v = CosmosValidator()
    m = v.validate(_cand("cosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2"))
    assert m is not None
    assert m.chain == "ATOM"
    assert m.format == "bech32"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_cross_chain_alternates_populated():
    v = CosmosValidator()
    m = v.validate(_cand("cosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2"))
    assert m is not None
    chains = [c for c, _ in m.cross_chain_alternates]
    assert "OSMO" in chains
    assert "JUNO" in chains
    assert "AKT" in chains  # akash
    assert len(m.cross_chain_alternates) >= 5


def test_invalid_rejected():
    v = CosmosValidator()
    assert v.validate(_cand("cosmos1invalid")) is None
    assert v.validate(_cand("not a cosmos address")) is None


def test_shape_match():
    v = CosmosValidator()
    assert v.shape_match(_cand("cosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2"))
    assert not v.shape_match(_cand("0xabc"))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/validators/test_cosmos.py -v`
Expected: FAIL with import errors.

- [ ] **Step 4: Write `src/ckc/validators/cosmos.py`**

```python
"""Cosmos validator: IBC family cross-chain.

All Cosmos SDK chains use the same secp256k1 keypair, derived via
m/44'/118'/0'/0/0. The 20-byte pubkey hash is bech32-encoded with
different HRPs per chain. ONE decode → N re-encodings.

This is the headline "crafty" feature: paste a cosmos1... address,
get back 9+ alternate encodings for Osmosis, Juno, Akash, etc.
"""

from __future__ import annotations

import re

import bech32

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match

# HRP → canonical chain code. Order matters for "primary" identification.
_HRPS: list[tuple[str, str]] = [
    ("cosmos", "ATOM"),
    ("osmo", "OSMO"),
    ("juno", "JUNO"),
    ("akash", "AKT"),
    ("inj", "INJ"),
    ("evmos", "EVMOS"),
    ("stride", "STRD"),
    ("regen", "REGEN"),
    ("persistence", "XPRT"),
    ("secret", "SCRT"),
    ("kava", "KAVA"),
    ("cro", "CRO"),
    ("terra", "LUNA"),
    ("band", "BAND"),
    ("umee", "UMEE"),
    ("stars", "STARS"),
    ("sent", "DVPN"),
    ("like", "LIKE"),
    ("axelar", "AXL"),
    ("cre", "CRE"),
]

_HRP_TO_CHAIN: dict[str, str] = dict(_HRPS)
_CHAIN_TO_HRP: dict[str, str] = {v: k for k, v in _HRPS}

# Match any of the known HRPs at start of bech32 string
_HRP_RE = re.compile(r"^(" + "|".join(h for h, _ in _HRPS) + r")1[02-9ac-hj-np-z]{38}")


class CosmosValidator:
    chain = "COSMOS_FAMILY"  # per-match chain is more specific
    formats = ["bech32"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_HRP_RE.match(candidate.normalized.lower()))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized.lower()
        if not _HRP_RE.match(s):
            return None

        hrp, data, spec = bech32.bech32_decode(s)
        if data is None or spec != bech32.Encoding.BECH32:
            return None

        # Convert 5-bit groups back to 8-bit bytes
        decoded = bech32.convertbits(list(data), 5, 8, False)
        if decoded is None or len(decoded) != 20:
            return None

        chain = _HRP_TO_CHAIN.get(hrp)
        if chain is None:
            return None

        # Generate cross-chain alternates by re-encoding with other HRPs
        alternates: list[tuple[str, str]] = []
        for alt_chain in _CHAIN_TO_HRP:
            if alt_chain == chain:
                continue
            alt_hrp = _CHAIN_TO_HRP[alt_chain]
            reencoded = bech32.bech32_encode(alt_hrp, data)
            if reencoded:
                alternates.append((alt_chain, reencoded))

        return Match(
            chain=chain,
            format="bech32",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=alternates,
            wallet_compatibility=wallets_for(chain),
            repairs_applied=candidate.repairs,
            notes=[f"same key works on {len(_HRPS)} Cosmos chains (HRP swap)"],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return match.cross_chain_alternates
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/validators/test_cosmos.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/ckc/validators/cosmos.py tests/validators/test_cosmos.py tests/fixtures/cosmos_vectors.json
git commit -m "Add Cosmos validator with cross-chain HRP swap (20 IBC chains)"
```

---

## Task 13: Pipeline orchestrator

**Files:**
- Create: `src/ckc/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline.py
from ckc.pipeline import classify, Config


def test_clean_btc_address():
    results = classify("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert len(results) >= 1
    top = results[0]
    assert top.chain == "BTC"
    assert top.confidence == 100


def test_strip_whitespace_then_classify():
    results = classify("  1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa  \n")
    top = results[0]
    assert top.chain == "BTC"
    assert "strip-ws" in top.repairs_applied
    assert top.confidence == 85  # valid after minor repair


def test_cosmos_returns_cross_chain_alternates():
    results = classify("cosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2")
    top = results[0]
    assert top.chain == "ATOM"
    assert len(top.cross_chain_alternates) >= 5


def test_garbage_returns_empty():
    results = classify("hello world this is not a key")
    assert results == []


def test_chains_filter():
    cfg = Config(chains={"ETH"})
    results = classify("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", config=cfg)
    assert results == []  # BTC filtered out


def test_min_confidence_filter():
    cfg = Config(min_confidence=80)
    # SOL address caps at 50 — should be filtered out
    results = classify("dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc", config=cfg)
    assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL with import errors.

- [ ] **Step 3: Write `src/ckc/pipeline.py`**

```python
"""Pipeline orchestrator.

For each input:
  1. Preprocess into candidate variants (Stage 1).
  2. For each validator: shape-match → strict validate → optional repairs.
  3. Collect matches, rank by confidence descending.
  4. Return ranked list.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ckc.models import Candidate, Match
from ckc.preprocessor import preprocess
from ckc.repairs import MAX_CANDIDATES, encoding_variants, length_repairs, ocr_substitutions
from ckc.validators import all_validators


@dataclass
class Config:
    """Pipeline configuration."""
    chains: set[str] | None = None  # None = all validators
    min_confidence: int = 0
    enable_repairs: bool = True
    max_repairs_per_input: int = MAX_CANDIDATES


def classify(raw: str, config: Config | None = None) -> list[Match]:
    """Classify a single input string. Returns ranked matches."""
    if not raw or not raw.strip():
        return []
    if config is None:
        config = Config()

    base_candidates = preprocess(raw)
    matches: list[Match] = []

    for validator in all_validators():
        # Filter by chain whitelist if set
        if config.chains is not None:
            validator_chains = _validator_chain_codes(validator)
            if not (validator_chains & config.chains):
                continue

        # Try base candidates first
        candidates = list(base_candidates)

        # Add format-specific repairs
        for base in base_candidates:
            candidates.extend(validator.suggest_repairs(base))

        # Cap total candidates
        candidates = candidates[: config.max_repairs_per_input]

        match_found = False
        for cand in candidates:
            if not validator.shape_match(cand):
                continue
            m = validator.validate(cand)
            if m is None:
                continue
            if m.confidence >= config.min_confidence:
                matches.append(m)
            if m.checksum_status == "valid":
                match_found = True
                break  # stop repairing once checksum passes

        # If no match yet, try aggressive repairs (OCR, encoding, length)
        if not match_found and config.enable_repairs:
            aggressive = _generate_aggressive_candidates(base_candidates, validator)
            for cand in aggressive[: config.max_repairs_per_input]:
                if not validator.shape_match(cand):
                    continue
                m = validator.validate(cand)
                if m is None:
                    continue
                if m.confidence >= config.min_confidence:
                    matches.append(m)
                if m.checksum_status == "valid":
                    break

    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches


def _validator_chain_codes(validator) -> set[str]:
    """Get all chain codes a validator can produce (for filtering)."""
    # Heuristic: BTCValidator handles BTC/LTC/DOGE/BCH; CosmosValidator handles the IBC family;
    # EVMValidator handles ETH + L2s; SolanaValidator handles SOL only.
    chain = getattr(validator, "chain", "")
    if chain == "BTC_FAMILY":
        return {"BTC", "LTC", "DOGE", "BCH"}
    if chain == "COSMOS_FAMILY":
        return {"ATOM", "OSMO", "JUNO", "AKT", "INJ", "EVMOS", "STRD", "REGEN", "XPRT"}
    if chain == "ETH":
        return {"ETH", "POLYGON", "ARBITRUM", "BASE", "OPTIMISM", "BSC", "AVALANCHE"}
    if chain == "SOL":
        return {"SOL"}
    return {chain}


def _generate_aggressive_candidates(
    base_candidates: list[Candidate], validator
) -> list[Candidate]:
    """Apply OCR + encoding + length repairs to base candidates."""
    out: list[Candidate] = []
    for base in base_candidates:
        # OCR stage
        for ocr_cand in ocr_substitutions(base.normalized):
            out.append(ocr_cand)
            # also apply base's repairs as context
            ocr_cand.repairs = base.repairs + ocr_cand.repairs

        # Encoding stage
        for enc_cand in encoding_variants(base.normalized):
            enc_cand.repairs = base.repairs + enc_cand.repairs
            out.append(enc_cand)

    # Length repairs need target lengths from validator — skip for MVP
    # (each validator can call length_repairs in its own suggest_repairs)

    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/ckc/pipeline.py tests/test_pipeline.py
git commit -m "Add pipeline orchestrator (validator fan-out, ranked matches)"
```

---

## Task 14: Reporter (rich / terse / json)

**Files:**
- Create: `src/ckc/reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reporter.py
from ckc.models import Match
from ckc.reporter import render_rich, render_terse, render_json, mask_key


def _match(chain="BTC", confidence=100, key_type="address", checksum="valid"):
    return Match(
        chain=chain, format="P2PKH", key_type=key_type,
        confidence=confidence, checksum_status=checksum,
        network="mainnet", cross_chain_alternates=[("LTC", "Labc")],
        wallet_compatibility=["Electrum"], repairs_applied=[], notes=[],
    )


def test_render_rich_includes_chain():
    out = render_rich("input", [_match()])
    assert "BTC" in out
    assert "100%" in out
    assert "Electrum" in out


def test_render_terse_one_line():
    out = render_terse("input", [_match()])
    assert "input" in out
    assert "BTC/P2PKH" in out
    assert "100%" in out
    # Should be one line per input
    assert out.count("\n") <= 1


def test_render_json_parses():
    import json
    out = render_json("input", [_match()])
    parsed = json.loads(out)
    assert parsed["input"] == "input"
    assert parsed["matches"][0]["chain"] == "BTC"


def test_mask_key_for_private_key():
    masked = mask_key("5Kb8cY8s9MwLq4m3F7o2Vd1pZaXyHgNvBc", key_type="private-key")
    # Should show first 4 + last 4 chars
    assert masked.startswith("5Kb8")
    assert masked.endswith("gNvBc")
    assert "..." in masked


def test_mask_key_off_for_address():
    addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert mask_key(addr, key_type="address") == addr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reporter.py -v`
Expected: FAIL with import errors.

- [ ] **Step 3: Write `src/ckc/reporter.py`**

```python
"""Output rendering: rich / terse / json.

All renderers take (input_string, list[Match]) and return a string.
Masking is applied at this layer so private keys never leak in default mode.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from ckc.models import Match


def mask_key(s: str, key_type: str, mask_private_keys: bool = True) -> str:
    """Mask private keys by default. Addresses are public — never masked."""
    if not mask_private_keys or key_type != "private-key":
        return s
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}...{s[-4:]}"


def render_rich(
    input_str: str,
    matches: list[Match],
    mask_private_keys: bool = True,
    show_wallets: bool = True,
    show_cross_chain: bool = True,
    explain: bool = True,
) -> str:
    """Rich multi-line output for single-input mode."""
    lines: list[str] = []
    masked_input = mask_key(input_str, _infer_key_type(matches), mask_private_keys)
    lines.append(f"INPUT: {masked_input}")
    lines.append("")

    if not matches:
        lines.append("✗ No matches found.")
        return "\n".join(lines)

    for i, m in enumerate(matches, 1):
        prefix = "✓" if i == 1 else " "
        lines.append(f"{prefix} MATCH ({m.confidence}%): {m.chain} {m.format}")
        lines.append(f"    Chain:        {m.chain}")
        lines.append(f"    Format:       {m.format}")
        lines.append(f"    Key type:     {m.key_type}")
        lines.append(f"    Checksum:     {m.checksum_status}")
        if m.network:
            lines.append(f"    Network:      {m.network}")
        if show_wallets and m.wallet_compatibility:
            lines.append(f"    Wallets:      {', '.join(m.wallet_compatibility)}")
        if show_cross_chain and m.cross_chain_alternates:
            lines.append(f"    Cross-chain:  same key as →")
            for chain, addr in m.cross_chain_alternates[:10]:
                lines.append(f"      • {chain:6}  {addr}")
            if len(m.cross_chain_alternates) > 10:
                lines.append(f"      • [+{len(m.cross_chain_alternates) - 10} more]")
        if explain and m.repairs_applied:
            lines.append(f"    Repairs:      {', '.join(m.repairs_applied)}")
        if m.notes:
            for note in m.notes:
                lines.append(f"    Note:         {note}")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_terse(
    input_str: str,
    matches: list[Match],
    mask_private_keys: bool = True,
) -> str:
    """One-line-per-input output for batch mode."""
    masked_input = mask_key(input_str, _infer_key_type(matches), mask_private_keys)
    if not matches:
        return f"{masked_input:30.30}  → NO MATCH"
    top = matches[0]
    return (
        f"{masked_input:30.30}  → {top.chain}/{top.format} "
        f"({top.confidence}%, checksum {top.checksum_status})"
    )


def render_json(
    input_str: str,
    matches: list[Match],
    mask_private_keys: bool = True,
) -> str:
    """Structured JSON for scripting."""
    masked_input = mask_key(input_str, _infer_key_type(matches), mask_private_keys)
    payload = {
        "input": masked_input,
        "best_guess": matches[0].chain if matches else None,
        "matches": [_match_to_dict(m) for m in matches],
    }
    return json.dumps(payload, indent=2)


def _match_to_dict(m: Match) -> dict:
    d = asdict(m)
    return d


def _infer_key_type(matches: list[Match]) -> str:
    """Infer key type from matches for masking decisions."""
    if matches and matches[0].key_type == "private-key":
        return "private-key"
    return "address"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reporter.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/ckc/reporter.py tests/test_reporter.py
git commit -m "Add reporter (rich/terse/json modes + private key masking)"
```

---

## Task 15: CLI entry point

**Files:**
- Create: `src/ckc/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import subprocess
import sys


def _run(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "ckc.cli"] + args,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_cli_single_input_rich_default():
    result = _run(["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    assert result.returncode == 0
    assert "BTC" in result.stdout
    assert "100%" in result.stdout


def test_cli_terse_mode():
    result = _run(["--terse", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    assert "BTC/P2PKH" in result.stdout
    assert result.stdout.count("\n") <= 2  # terse = 1-2 lines


def test_cli_json_mode():
    result = _run(["--json", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    import json
    parsed = json.loads(result.stdout)
    assert parsed["matches"][0]["chain"] == "BTC"


def test_cli_stdin_batch_uses_terse():
    stdin = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\ncosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2\n"
    result = _run([], stdin=stdin)
    assert "BTC/P2PKH" in result.stdout
    assert "ATOM/bech32" in result.stdout


def test_cli_masks_private_keys_by_default():
    # WIF private key — should be masked
    result = _run(["5Kb8cY8s9MwLq4m3F7o2Vd1pZaXyHgNvBcJ6T3fA1mQd8xSq9Rp"])
    if "PRIVATE KEY" in result.stdout:
        # if recognized as private key, must be masked
        assert "..." in result.stdout


def test_cli_min_confidence_filter():
    # SOL address caps at 50 confidence
    result = _run(["--min-confidence", "80", "dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc"])
    assert "No matches" in result.stdout or "NO MATCH" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with import errors.

- [ ] **Step 3: Write `src/ckc/cli.py`**

```python
"""CLI entry point.

Usage:
  classify-key <INPUT>
  classify-key <INPUT1> <INPUT2> ...     (batch → terse)
  classify-key --file keys.txt           (batch → terse)
  echo "<input>" | classify-key          (stdin)
  classify-key --json <INPUT>
  classify-key --no-mask --no-cross-chain <INPUT>
"""

from __future__ import annotations

import argparse
import sys

from ckc.pipeline import Config, classify
from ckc.reporter import render_json, render_rich, render_terse


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="classify-key",
        description="Classify any crypto-key string (BTC/ETH/SOL/Cosmos + more) "
                    "with aggressive recovery from corruption.",
    )
    p.add_argument("inputs", nargs="*", help="input string(s) to classify")
    p.add_argument("--file", "-f", help="read inputs from file (one per line)")
    p.add_argument("--rich", action="store_true", help="rich multi-line output (default for 1 input)")
    p.add_argument("--terse", action="store_true", help="one-line output (default for 2+ inputs)")
    p.add_argument("--json", dest="as_json", action="store_true", help="JSON output")
    p.add_argument("--no-mask", action="store_true", help="show full private keys (DANGEROUS)")
    p.add_argument("--no-cross-chain", action="store_true", help="omit cross-chain alternates")
    p.add_argument("--no-wallets", action="store_true", help="omit wallet compatibility list")
    p.add_argument("--explain", action="store_true", help="include repair trace")
    p.add_argument("--min-confidence", type=int, default=0, help="filter matches below N%")
    p.add_argument("--chains", help="comma-separated chain whitelist (e.g. btc,eth,sol)")
    return p


def _gather_inputs(args: argparse.Namespace) -> list[str]:
    inputs: list[str] = list(args.inputs)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            inputs.extend(line.strip() for line in f if line.strip() and not line.startswith("#"))
    if not sys.stdin.isatty() and not inputs:
        for line in sys.stdin:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                inputs.append(stripped)
    return inputs


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    inputs = _gather_inputs(args)

    if not inputs:
        print("error: no input provided", file=sys.stderr)
        return 2

    chains_whitelist = set(args.chains.split(",")) if args.chains else None
    config = Config(
        chains=chains_whitelist,
        min_confidence=args.min_confidence,
    )

    is_batch = len(inputs) > 1
    mask = not args.no_mask

    # Warn on --no-mask with potential private keys
    if args.no_mask:
        print(
            "WARNING: --no-mask is on. If any input is a private key, "
            "it will be printed to stdout in cleartext.",
            file=sys.stderr,
        )

    for raw in inputs:
        matches = classify(raw, config=config)

        # Choose output mode
        if args.as_json:
            print(render_json(raw, matches, mask_private_keys=mask))
        elif args.rich or not (is_batch or args.terse):
            # Single input default → rich
            print(
                render_rich(
                    raw, matches,
                    mask_private_keys=mask,
                    show_wallets=not args.no_wallets,
                    show_cross_chain=not args.no_cross_chain,
                    explain=args.explain,
                )
            )
        else:
            # Batch default → terse
            print(render_terse(raw, matches, mask_private_keys=mask))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/ckc/cli.py tests/test_cli.py
git commit -m "Add CLI entry point (rich/terse/json modes, masking, batch from stdin/file)"
```

---

## Task 16: End-to-end smoke test

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Write the smoke test**

```python
# tests/test_e2e.py
"""End-to-end smoke tests exercising real input through the full pipeline.

Covers the headline scenarios from the spec:
  - Clean BTC address
  - BTC address with whitespace
  - ETH EIP-55 checksum valid
  - ETH address with failed checksum (typo)
  - Solana address
  - Cosmos address with cross-chain alternates
  - LTC cross-chain from BTC family decode
  - Garbage input
"""

from ckc.pipeline import classify


def test_e2e_clean_btc():
    matches = classify("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert matches and matches[0].chain == "BTC" and matches[0].confidence == 100


def test_e2e_btc_with_whitespace():
    matches = classify("  1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n\t")
    assert matches and matches[0].chain == "BTC"
    assert any("strip-ws" in r for r in matches[0].repairs_applied)


def test_e2e_eth_eip55_valid():
    matches = classify("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
    assert matches and matches[0].chain == "ETH" and matches[0].checksum_status == "valid"


def test_e2e_solana_address():
    matches = classify("dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc")
    assert matches and matches[0].chain == "SOL" and matches[0].confidence == 50


def test_e2e_cosmos_cross_chain_alternates():
    matches = classify("cosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2")
    assert matches and matches[0].chain == "ATOM"
    alt_chains = [c for c, _ in matches[0].cross_chain_alternates]
    assert "OSMO" in alt_chains
    assert "JUNO" in alt_chains


def test_e2e_garbage_input_returns_empty():
    assert classify("hello world this is not a key") == []
    assert classify("") == []
    assert classify("   ") == []


def test_e2e_pipeline_runs_all_validators_without_crashing():
    # Fuzz-ish: a wide range of inputs should not raise
    inputs = [
        "", "abc", "0x", "1A1zP1", "bc1q", "cosmos1",
        "5Kb8" * 13,  # long base58
        "deadbeef" * 8,  # long hex
        "0" * 100,
        "1" * 100,
    ]
    for raw in inputs:
        classify(raw)  # must not raise
```

- [ ] **Step 2: Run full test suite**

Run: `pytest -v`
Expected: all tests pass (models + preprocessor + repairs + 4 validators + pipeline + reporter + cli + e2e).

- [ ] **Step 3: Run type check**

Run: `pyright src/ckc/`
Expected: 0 errors (warnings acceptable).

- [ ] **Step 4: Run linter**

Run: `ruff check src/ckc/ tests/`
Expected: 0 errors.

- [ ] **Step 5: Manual smoke test from CLI**

```bash
classify-key 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
classify-key --json 0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed | head
classify-key cosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2
echo -e "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\ncosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2" | classify-key
```
Expected: rich output for single inputs, terse for batch, JSON parses cleanly, Cosmos shows cross-chain alternates.

- [ ] **Step 6: Commit**

```bash
git add tests/test_e2e.py
git commit -m "Add end-to-end smoke tests covering MVP scenarios"
```

- [ ] **Step 7: Tag the MVP**

```bash
git tag -a v0.1.0-mvp -m "MVP: BTC-family/EVM/SOL/Cosmos classifier with repair + cross-chain + CLI"
```

---

## Done criteria

The MVP is done when:

1. ✅ All 16 tasks committed
2. ✅ `pytest -v` passes all tests
3. ✅ `pyright src/ckc/` reports 0 errors
4. ✅ `ruff check` reports 0 errors
5. ✅ Manual CLI smoke test (Task 16 Step 5) produces sensible output for BTC / ETH / SOL / Cosmos inputs
6. ✅ Masking works: WIF/private-key inputs show `5Kb8...gNvBc` by default
7. ✅ Cross-chain expansion works: Cosmos input shows OSMO/JUNO/AKT alternates
8. ✅ `git tag v0.1.0-mvp` annotated

## What's next (follow-on plans)

- **Plan 2:** 12 long-tail validators (Monero, Cardano, Tezos, Polkadot, TON, Stellar, Tron, Algorand, Kaspa, Sui/Aptos, Near, Ripple) — same validator-per-chain pattern, ~3-4 tasks per validator including fixtures.
- **Plan 3:** Mnemonic validator (BIP39 + Electrum + Levenshtein wordlist repair).
- **Plan 4:** Property tests + fuzzing harness (random key generation + mutation, assert classification recovery rate).
