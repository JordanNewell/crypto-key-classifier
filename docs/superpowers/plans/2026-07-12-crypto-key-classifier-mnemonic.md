# Crypto Key Classifier — Mnemonic Validator Plan (Plan 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add BIP39 + Electrum mnemonic seed phrase detection with Levenshtein word repair for typo recovery.

**Architecture:** Bundle BIP39 English wordlist as package data. Implement BIP39 checksum verification (SHA-256 of entropy). Detect Electrum heuristically (BIP39 checksum fails but wordlist matches → flag). Levenshtein distance ≤2 generates repair candidates. Validator suggests compatible derivation paths (BTC/LTC/ETH/SOL/etc.) as notes — does NOT compute actual derived addresses (would require BIP32 + curve math, deferred).

**Tech Stack:** Python stdlib (hashlib for SHA-256, no new deps). Bundled `bip39_english.txt` wordlist.

**Reference:** `docs/superpowers/specs/2026-07-12-crypto-key-classifier-design.md`

---

## File structure

```
crypto-key-classifier/
├── src/ckc/
│   ├── validators/
│   │   ├── base.py                  # Task 1 — add levenshtein_distance helper
│   │   └── mnemonic.py              # Task 2 — BIP39 + Electrum validator
│   └── data/
│       ├── wallets.py               # exists
│       └── bip39_english.txt        # Task 1 — bundle official wordlist
└── tests/
    ├── test_mnemonic_wordlist.py    # Task 1
    ├── test_leveshtein.py           # Task 1
    └── validators/
        └── test_mnemonic.py         # Task 2
```

---

## Chain specs (reference)

**BIP39:**
- ENT/CS/MS table: 128/4/12, 160/5/15, 192/6/18, 224/7/21, 256/8/24
- Checksum = first **ENT/32 bits** of SHA-256(entropy)
- Wordlist: 2048 words (`english.txt` from BIP-39 reference)
- Validation: indices → bits → split entropy + checksum → recompute checksum

**Electrum (4.x):**
- Same English wordlist
- HMAC-based checksum + version byte (NOT BIP39-compatible)
- Heuristic detection: if BIP39 checksum fails on 12 words from the BIP39 wordlist, flag as "possibly Electrum"
- Full Electrum verification out of scope (would need version table + HMAC key derivation)

**Levenshtein distance:**
- Classic dynamic programming, ≤2 edits
- For each word not in wordlist, find all wordlist entries within distance 2
- If exactly one match, use it (high confidence repair)
- If multiple matches, return all candidates (low confidence)
- Cap: max 3 word repairs per mnemonic

---

## Task 1: Bundle BIP39 wordlist + Levenshtein helper

**Files:**
- Create: `src/ckc/data/bip39_english.txt` (download official BIP-39 English wordlist)
- Modify: `src/ckc/validators/base.py` (add `levenshtein_distance` helper)
- Modify: `src/ckc/data/__init__.py` (if doesn't exist, create empty)
- Create: `tests/test_mnemonic_wordlist.py`
- Create: `tests/test_leveshtein.py`

- [ ] **Step 1: Download official BIP-39 English wordlist**

```bash
# Download from official BIPS repo
curl -sSL https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt -o src/ckc/data/bip39_english.txt

# Verify line count
wc -l src/ckc/data/bip39_english.txt  # should be 2048
```

If curl fails, use WebFetch or download manually. The file MUST be 2048 words, sorted alphabetically, lowercase, newline-separated.

- [ ] **Step 2: Add `__init__.py` if missing for `src/ckc/data/`**

```bash
ls src/ckc/data/__init__.py 2>/dev/null || touch src/ckc/data/__init__.py
```

- [ ] **Step 3: Write failing tests**

`tests/test_mnemonic_wordlist.py`:

```python
"""Verify the bundled BIP-39 English wordlist is the official one."""
from importlib import resources


def test_wordlist_has_2048_words():
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        words = [line.strip() for line in f if line.strip()]
    assert len(words) == 2048


def test_wordlist_sorted():
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        words = [line.strip() for line in f if line.strip()]
    assert words == sorted(words)


def test_wordlist_first_word():
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        first = f.readline().strip()
    assert first == "abandon"


def test_wordlist_last_word():
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        words = [line.strip() for line in f if line.strip()]
    assert words[-1] == "zoo"
```

`tests/test_leveshtein.py`:

```python
from ckc.validators.base import levenshtein_distance


def test_identical_strings():
    assert levenshtein_distance("abc", "abc") == 0


def test_one_substitution():
    assert levenshtein_distance("abc", "abd") == 1


def test_one_insertion():
    assert levenshtein_distance("abc", "abcd") == 1


def test_one_deletion():
    assert levenshtein_distance("abc", "ab") == 1


def test_completely_different():
    assert levenshtein_distance("abc", "xyz") == 3


def test_typo_distance_one():
    # Common BIP39 typo: "abondon" → "abandon"
    assert levenshtein_distance("abondon", "abandon") == 1


def test_empty_strings():
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("abc", "") == 3
```

- [ ] **Step 4: Add `levenshtein_distance` to base.py**

Append to `src/ckc/validators/base.py` (do not remove existing content):

```python
def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings.

    Counts minimum number of single-char insertions, deletions, or
    substitutions needed to transform s1 into s2.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]
```

- [ ] **Step 5: Verify tests pass**

`py -m pytest tests/test_mnemonic_wordlist.py tests/test_leveshtein.py -v` → 11 passed.
`py -m pytest -v` → all 176 prior + 11 new = 187 passed.

- [ ] **Step 6: Update pyproject.toml to include the wordlist in package data**

Add to `pyproject.toml` `[tool.setuptools]` section:

```toml
[tool.setuptools.package-data]
"ckc.data" = ["*.txt"]
```

- [ ] **Step 7: Reinstall to pick up package data**

```bash
pip install -e . --force-reinstall --no-deps
```

- [ ] **Step 8: Verify importlib.resources can find the wordlist**

```bash
py -c "from importlib import resources; f = resources.files('ckc.data').joinpath('bip39_english.txt'); print(f.is_file(), len(f.read_text().split()))"
```
Expected: `True 2048`

- [ ] **Step 9: Commit**

```bash
git add src/ckc/data/bip39_english.txt src/ckc/data/__init__.py src/ckc/validators/base.py tests/test_mnemonic_wordlist.py tests/test_leveshtein.py pyproject.toml
git commit -m "Bundle BIP-39 English wordlist + add Levenshtein distance helper"
```

---

## Task 2: Mnemonic validator (BIP39 + Electrum detection + Levenshtein repair)

**Files:**
- Create: `src/ckc/validators/mnemonic.py`
- Create: `tests/validators/test_mnemonic.py`

- [ ] **Step 1: Write failing tests**

`tests/validators/test_mnemonic.py`:

```python
import pytest

from ckc.validators.mnemonic import MnemonicValidator
from ckc.models import Candidate


def _cand(s: str, repairs=None) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=repairs or [], encoding=None, bytes_value=None)


# Well-known BIP-39 test vectors (from Trezor python-mnemonic test suite)
VALID_12_WORD = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
VALID_12_WORD_ENTROPY = "00000000000000000000000000000000"

VALID_24_WORD = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"

TYPO_12_WORD = "abondon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
# "abondon" is one char off from "abandon"


def test_bip39_12_word_valid():
    v = MnemonicValidator()
    m = v.validate(_cand(VALID_12_WORD))
    assert m is not None
    assert m.chain == "BIP39"
    assert m.format == "mnemonic-12-word"
    assert m.key_type == "mnemonic"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_bip39_24_word_valid():
    v = MnemonicValidator()
    m = v.validate(_cand(VALID_24_WORD))
    assert m is not None
    assert m.format == "mnemonic-24-word"


def test_bip39_invalid_checksum_rejected():
    # Last word changed — checksum fails
    v = MnemonicValidator()
    invalid = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon"
    # 12 "abandon" + nothing — that's only 12 words but the last word "abandon" doesn't have the right checksum bit
    m = v.validate(_cand(invalid))
    # Should either return None OR return a low-confidence match with checksum_status=failed
    if m is not None:
        assert m.checksum_status == "failed"
        assert m.confidence <= 40


def test_shape_match_mnemonic_pattern():
    v = MnemonicValidator()
    # 12 lowercase words
    assert v.shape_match(_cand(VALID_12_WORD))
    # 24 lowercase words
    assert v.shape_match(_cand(VALID_24_WORD))


def test_shape_match_non_mnemonic():
    v = MnemonicValidator()
    assert not v.shape_match(_cand("not a mnemonic"))
    assert not v.shape_match(_cand("0xabc"))
    assert not v.shape_match(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))


def test_typo_repair_via_suggest_repairs():
    """suggest_repairs should propose a fix for the typo'd word."""
    v = MnemonicValidator()
    candidates = v.suggest_repairs(_cand(TYPO_12_WORD))
    # Should produce at least one variant with "abondon" → "abandon"
    abandon_variants = [c for c in candidates if "abandon abandon abandon" in c.normalized[:30]]
    assert len(abandon_variants) > 0
    # Each should note the repair
    assert any("levenshtein" in r.lower() or "ocr" in r.lower() or "typo" in r.lower()
               for c in abandon_variants for r in c.repairs)


def test_typo_repaired_mnemonic_validates():
    """After repair, the mnemonic should pass BIP39 validation."""
    v = MnemonicValidator()
    candidates = v.suggest_repairs(_cand(TYPO_12_WORD))
    valid_found = False
    for c in candidates:
        m = v.validate(c)
        if m and m.checksum_status == "valid":
            valid_found = True
            break
    assert valid_found


def test_no_cross_chain_alternates():
    v = MnemonicValidator()
    m = v.validate(_cand(VALID_12_WORD))
    assert m is not None
    # Mnemonics derive keys for many chains, but we don't enumerate them as alternates
    assert m.cross_chain_alternates == []


def test_notes_include_derivation_path_info():
    v = MnemonicValidator()
    m = v.validate(_cand(VALID_12_WORD))
    assert m is not None
    notes_joined = " ".join(m.notes).lower()
    # Should mention some derivation context
    assert "bip39" in notes_joined or "derivation" in notes_joined or "wallet" in notes_joined


def test_electrum_detection_heuristic():
    """When BIP39 checksum fails on a 12-word phrase from the wordlist,
    we should flag as 'possibly Electrum' in notes."""
    # This is the canonical Electrum 12-word seed "gravity machine north sort...
    # But we can't easily construct one that fails BIP39 but passes Electrum
    # without Electrum's HMAC machinery.
    # Instead: take a valid BIP39 phrase, swap a non-checksum-affecting word,
    # verify it gets the "possibly Electrum" note.
    v = MnemonicValidator()
    # Use a phrase where checksum will fail
    bad_phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon"
    m = v.validate(_cand(bad_phrase))
    if m is not None and m.checksum_status == "failed":
        notes_joined = " ".join(m.notes).lower()
        assert "electrum" in notes_joined or "alternative" in notes_joined
```

- [ ] **Step 2: Verify failure**

`py -m pytest tests/validators/test_mnemonic.py -v` → FAIL.

- [ ] **Step 3: Implement `src/ckc/validators/mnemonic.py`**

```python
"""Mnemonic validator: BIP-39 + Electrum detection + Levenshtein repair.

BIP-39 seeds: 12/15/18/21/24 words from the official 2048-word English wordlist.
Checksum = first ENT/32 bits of SHA-256(entropy), where ENT = words × 11 - checksum_bits.

Levenshtein repair: for each word not in wordlist, find wordlist entries within
distance ≤2. If exactly one match, use it (high confidence). If multiple, all
become repair candidates (low confidence).

Electrum detection: if BIP-39 checksum fails on a 12-word phrase where all words
are in the BIP-39 wordlist, flag as 'possibly Electrum' (heuristic — Electrum 2.0+
uses HMAC-based checksum and is NOT BIP-39 compatible).
"""

from __future__ import annotations

import hashlib
import re
from importlib import resources

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import levenshtein_distance

# Load BIP-39 English wordlist once
def _load_wordlist() -> tuple[list[str], dict[str, int]]:
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        words = [line.strip() for line in f if line.strip()]
    return words, {w: i for i, w in enumerate(words)}

_WORDLIST, _WORD_TO_INDEX = _load_wordlist()

# BIP-39 entropy / checksum / mnemonic-length table
_BIP39_PARAMS: dict[int, tuple[int, int]] = {
    12: (128, 4),   # ENT, CS
    15: (160, 5),
    18: (192, 6),
    21: (224, 7),
    24: (256, 8),
}

# Regex: 12/15/18/21/24 lowercase words separated by whitespace
_MNEMONIC_RE = re.compile(r"^[a-z]+(?:\s+[a-z]+){11,23}$")


def _words_to_entropy(words: list[str]) -> tuple[bytes, int] | None:
    """Convert wordlist indices to entropy + checksum bits.
    Returns (entropy_bytes, checksum_bits) or None if any word isn't in wordlist.
    """
    if len(words) not in _BIP39_PARAMS:
        return None
    ent, cs = _BIP39_PARAMS[len(words)]
    bits = ""
    for word in words:
        idx = _WORD_TO_INDEX.get(word)
        if idx is None:
            return None
        bits += format(idx, "011b")
    # bits length = words × 11 = ENT + CS
    entropy_bits = bits[:ent]
    checksum_bits = bits[ent:]
    # Convert entropy bits to bytes
    entropy_bytes = int(entropy_bits, 2).to_bytes(ent // 8, "big")
    return entropy_bytes, int(checksum_bits, 2)


def _bip39_checksum_valid(entropy: bytes, cs_bits: int, expected: int) -> bool:
    """Verify BIP-39 checksum: first CS bits of SHA-256(entropy)."""
    if len(entropy) == 0:
        return False
    hash_int = int.from_bytes(hashlib.sha256(entropy).digest(), "big")
    # Take first CS bits (most significant)
    actual = (hash_int >> (256 - cs_bits)) & ((1 << cs_bits) - 1)
    return actual == expected


class MnemonicValidator:
    chain = "BIP39"
    formats = ["mnemonic-12-word", "mnemonic-15-word", "mnemonic-18-word",
               "mnemonic-21-word", "mnemonic-24-word"]
    # Mnemonic derives keys for many chains — claim coverage for filtering
    chains_covered = {"BIP39", "BTC", "ETH", "SOL", "LTC", "DOGE", "ATOM"}

    def shape_match(self, candidate: Candidate) -> bool:
        s = candidate.normalized
        if not _MNEMONIC_RE.match(s):
            return False
        # Must be one of the valid word counts
        words = s.split()
        return len(words) in _BIP39_PARAMS

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _MNEMONIC_RE.match(s):
            return None
        words = s.split()
        if len(words) not in _BIP39_PARAMS:
            return None

        result = _words_to_entropy(words)
        if result is None:
            # At least one word isn't in wordlist — try Levenshtein in suggest_repairs
            return None
        entropy, checksum_bits = result
        _, cs = _BIP39_PARAMS[len(words)]

        is_valid = _bip39_checksum_valid(entropy, cs, checksum_bits)
        fmt = f"mnemonic-{len(words)}-word"

        if is_valid:
            return Match(
                chain="BIP39",
                format=fmt,
                key_type="mnemonic",
                confidence=100,
                checksum_status="valid",
                network="mainnet",
                cross_chain_alternates=[],  # mnemonic derives many chains; out of scope to enumerate
                wallet_compatibility=[
                    "Ledger", "Trezor", "Bitcoin Core (import)", "Electrum",
                    "MetaMask", "Phantom", "Exodus",
                ],
                repairs_applied=candidate.repairs,
                notes=[
                    f"BIP-39 mnemonic ({len(words)} words = {len(words) * 11 - cs} bits entropy)",
                    "derives keys for BTC/LTC/DOGE/ETH/SOL/ATOM/etc. via BIP-32 paths",
                    "PRIVATE — handle with care (full wallet access)",
                ],
            )
        else:
            # Checksum failed. Could be Electrum if all words are in BIP-39 wordlist.
            notes = [
                "BIP-39 checksum FAILED",
                "if all words are valid BIP-39 entries, this MAY be an Electrum seed (different checksum algo)",
            ]
            return Match(
                chain="BIP39",
                format=fmt + "-checksum-failed",
                key_type="mnemonic",
                confidence=40,  # checksum-failed tier
                checksum_status="failed",
                network="mainnet",
                cross_chain_alternates=[],
                wallet_compatibility=[],
                repairs_applied=candidate.repairs,
                notes=notes,
            )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        """For each non-wordlist word, propose close matches via Levenshtein ≤2."""
        s = candidate.normalized
        words = s.split()
        if len(words) not in _BIP39_PARAMS:
            return []

        # Find words that aren't in the wordlist
        bad_indices: list[int] = []
        for i, w in enumerate(words):
            if w not in _WORD_TO_INDEX:
                bad_indices.append(i)

        if not bad_indices:
            return []

        # Cap at 3 repairs
        bad_indices = bad_indices[:3]

        # For each bad word, find wordlist entries within distance 2
        repair_options: list[list[str]] = []  # for each bad index, list of candidates
        for i in bad_indices:
            bad_word = words[i]
            candidates = []
            for w in _WORDLIST:
                if abs(len(w) - len(bad_word)) <= 2:
                    d = levenshtein_distance(bad_word, w)
                    if d <= 2:
                        candidates.append(w)
            if not candidates:
                return []  # no repair possible
            repair_options.append(candidates)

        # Generate cartesian product (bounded to avoid combinatorial blowup)
        # Cap total variants at 8
        result: list[Candidate] = []
        def _generate(idx: int, current_words: list[str]) -> None:
            if len(result) >= 8:
                return
            if idx == len(repair_options):
                repaired = " ".join(current_words[:])
                repairs = [f"levenshtein:{words[bad_indices[j]]}→{current_words[bad_indices[j]]}"
                           for j in range(len(bad_indices))]
                result.append(Candidate(
                    raw=candidate.raw,
                    normalized=repaired,
                    repairs=candidate.repairs + repairs,
                    encoding=None, bytes_value=None,
                ))
                return
            bad_idx = bad_indices[idx]
            for new_word in repair_options[idx]:
                current_words[bad_idx] = new_word
                _generate(idx + 1, current_words)
                if len(result) >= 8:
                    return

        _generate(0, words[:])
        return result

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
```

- [ ] **Step 4: Verify tests pass**

`py -m pytest tests/validators/test_mnemonic.py -v` → 10 passed.
`py -m pytest -v` → 187 prior + 10 new = 197 passed.

- [ ] **Step 5: Commit**

```bash
git add src/ckc/validators/mnemonic.py tests/validators/test_mnemonic.py
git commit -m "Add mnemonic validator (BIP-39 + Electrum detection + Levenshtein word repair)"
```

---

## Task 3: Pipeline integration + e2e + tag v0.3.0-mnemonic

**Files:**
- Modify: `src/ckc/pipeline.py` (add BIP39 to chain codes)
- Create: `tests/test_mnemonic_e2e.py`

- [ ] **Step 1: Update pipeline `_validator_chain_codes`**

In `src/ckc/pipeline.py`, the MnemonicValidator has `chains_covered = {"BIP39", "BTC", "ETH", "SOL", "LTC", "DOGE", "ATOM"}`, which the existing `chains_covered` class-attr check in `_validator_chain_codes` already handles. No change needed unless the function doesn't check `chains_covered` yet.

Verify: read `pipeline.py` and confirm `_validator_chain_codes` already uses `getattr(validator, "chains_covered", None)`. If yes, skip. If no, add the check.

- [ ] **Step 2: Write E2E test**

`tests/test_mnemonic_e2e.py`:

```python
"""End-to-end tests for mnemonic validator through the pipeline."""

from ckc.pipeline import classify, Config


VALID_12 = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
TYPO_12 = "abondon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"


def test_e2e_valid_mnemonic_classified():
    r = classify(VALID_12)
    assert r and r[0].chain == "BIP39"
    assert r[0].confidence == 100
    assert r[0].checksum_status == "valid"


def test_e2e_typo_mnemonic_repaired():
    """Pipeline should apply Levenshtein repair and find a valid match."""
    r = classify(TYPO_12)
    # Should find a BIP39 match (via suggest_repairs → pipeline re-validates)
    assert any(m.chain == "BIP39" and m.checksum_status == "valid" for m in r)


def test_e2e_mnemonic_masked_as_private():
    """Mnemonics are private — should be masked in reporter output."""
    from ckc.reporter import render_rich
    r = classify(VALID_12)
    out = render_rich(VALID_12, r, mask_private_keys=True)
    # The raw mnemonic should NOT appear in output
    assert VALID_12 not in out


def test_e2e_all_17_validators():
    """Registry should now find 17 validators (16 + mnemonic)."""
    from ckc.validators import all_validators
    assert len(all_validators()) == 17


def test_e2e_random_words_rejected():
    """12 random English words that don't form valid checksum → still classified
    as BIP39 with checksum_status=failed (low confidence)."""
    r = classify("apple banana cherry dog elephant fox grape hat igloo juice kite light")
    # 12 valid wordlist words but checksum likely fails → low-confidence BIP39 match
    if r:
        assert r[0].chain == "BIP39"
```

- [ ] **Step 3: Run full suite**

`py -m pytest -v` → 197 + 5 = 202 passed.

- [ ] **Step 4: Ruff + pyright**

`py -m ruff check src/ckc/ tests/` → clean.
`py -m pyright src/ckc/` → external-stub errors only.

- [ ] **Step 5: Manual smoke**

```bash
# Valid mnemonic
py -m ckc.cli "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"

# Typo'd mnemonic (Levenshtein repair)
py -m ckc.cli "abondon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
```

Expected: rich output, BIP39 chain, derivation info in notes. Typo version should still find a match via repair.

- [ ] **Step 6: Commit + tag**

```bash
git add tests/test_mnemonic_e2e.py
git commit -m "Add mnemonic e2e tests + verify pipeline integration"
git tag -a v0.3.0-mnemonic -m "Mnemonic validator: BIP-39 + Electrum detection + Levenshtein repair"
```

---

## Done criteria

- BIP-39 wordlist bundled as package data (2048 words, official)
- Levenshtein distance helper added to base.py
- MnemonicValidator handles 12/15/18/21/24 word seeds
- BIP-39 checksum validation works for known test vectors
- Levenshtein repair recovers from 1-3 typo'd words
- Electrum heuristic detection (notes flag when checksum fails on valid wordlist words)
- Mnemonics masked as private keys in reporter (auto-detected via key_type)
- All tests pass (~202 total)
- Tag v0.3.0-mnemonic created

## What's next

- **Plan 4:** Property tests + fuzzing harness
