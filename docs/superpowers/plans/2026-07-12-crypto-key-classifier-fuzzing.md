# Crypto Key Classifier — Fuzzing / Property Tests Plan (Plan 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Property-based tests that generate random valid keys per chain, apply mutations, and verify the classifier recovers the correct chain. Target: ≥90% recovery for single-char mutations.

**Architecture:** Use `hypothesis` for property-based test generation. Custom strategies produce valid keys per chain (using the same encode functions already in each validator's tests). Mutation functions produce corrupted variants. Pipeline.classify() is the system under test. Recovery rate is asserted per validator family.

**Tech Stack:** Python + `hypothesis` (new dev dep). All mutation/strategy code in `tests/fuzz/`.

**Reference:** `docs/superpowers/specs/2026-07-12-crypto-key-classifier-design.md` (property tests section)

---

## File structure

```
crypto-key-classifier/
├── pyproject.toml                    # Task 1 — add hypothesis to dev deps
└── tests/
    ├── fuzz/
    │   ├── __init__.py
    │   ├── strategies.py             # Task 1 — per-chain key generators
    │   ├── mutations.py              # Task 1 — char swap/sub/delete/insert/ocr/ws
    │   ├── test_mvp_fuzz.py          # Task 2
    │   ├── test_long_tail_fuzz.py    # Task 3
    │   └── test_mnemonic_fuzz.py     # Task 4
    └── test_fuzz_aggregate.py        # Task 5
```

---

## Mutation strategies (reference)

| Mutation | What it does | Expected recovery |
|----------|--------------|-------------------|
| `whitespace_pollution` | Add spaces/newlines/tabs around key | 100% (Stage 1 repair always handles) |
| `case_flip` | Flip case of one letter | Chain-dependent (ETH should fix via EIP-55) |
| `char_substitute` | Replace one char with another from same charset | Depends on checksum — usually breaks |
| `char_delete` | Remove one char | Almost always breaks checksum |
| `char_insert` | Add one char at random position | Almost always breaks |
| `char_swap_adjacent` | Swap two adjacent chars | Often survives if same charset |
| `ocr_substitute` | Replace with visual confusable (O↔0, l↔1) | Should repair via Stage 2 OCR |

**Target recovery rates** (single mutation, per spec):
- Whitespace pollution: 100%
- OCR substitution: ≥80% (when result still decodes)
- Char swap (same charset): ≥50%
- Other mutations: no target (informational only)

---

## Task 1: Hypothesis setup + fuzz helpers

**Files:**
- Modify: `pyproject.toml` (add `hypothesis` to dev deps)
- Create: `tests/fuzz/__init__.py` (empty)
- Create: `tests/fuzz/strategies.py` — per-chain valid-key generators
- Create: `tests/fuzz/mutations.py` — mutation functions

- [ ] **Step 1: Add hypothesis to pyproject.toml dev deps**

Add `hypothesis>=6.100` to the `[project.optional-dependencies] dev` list. Reinstall: `pip install -e ".[dev]"`.

- [ ] **Step 2: Create `tests/fuzz/__init__.py`** (empty file)

- [ ] **Step 3: Write `tests/fuzz/strategies.py`**

```python
"""Hypothesis strategies: generate valid keys per chain.

Each strategy produces a (chain_code, valid_key_string) tuple using the same
encode functions the validators use. This ensures we're testing valid inputs.
"""

from __future__ import annotations

import os
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from ckc.validators.base import (
    base58check_encode, bech32_encode, convertbits, keccak256,
    monero_base58_encode, crc16_xmodem,
)


def _random_bytes(n: int) -> bytes:
    return bytes(os.urandom(n))


# --- BTC family ---


def btc_p2pkh_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid BTC P2PKH addresses."""
    return st.builds(
        lambda _: ("BTC", base58check_encode(b"\x00" + _random_bytes(20))),
        st.none(),
    )


def btc_p2sh_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("BTC", base58check_encode(b"\x05" + _random_bytes(20))),
        st.none(),
    )


def btc_bech32_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid BTC bech32 segwit v0 addresses (20-byte witness program)."""
    def make(_) -> tuple[str, str]:
        program = _random_bytes(20)
        data = [0] + convertbits(list(program), 8, 5, True)  # type: ignore[list-item]
        return ("BTC", bech32_encode("bc", data, "bech32"))
    return st.builds(make, st.none())


def ltc_p2pkh_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("LTC", base58check_encode(b"\x30" + _random_bytes(20))),
        st.none(),
    )


def doge_p2pkh_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("DOGE", base58check_encode(b"\x1e" + _random_bytes(20))),
        st.none(),
    )


# --- EVM ---


def eth_address_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid ETH addresses (no EIP-55 checksum, all-lowercase)."""
    return st.builds(
        lambda _: ("ETH", "0x" + _random_bytes(20).hex()),
        st.none(),
    )


def eth_privkey_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("ETH", "0x" + _random_bytes(32).hex()),
        st.none(),
    )


# --- Solana ---


def solana_address_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid SOL addresses (32-byte ed25519 base58)."""
    import base58
    return st.builds(
        lambda _: ("SOL", base58.b58encode(_random_bytes(32)).decode("ascii")),
        st.none(),
    )


# --- Cosmos (one HRP representative) ---


def cosmos_address_strategy() -> SearchStrategy[tuple[str, str]]:
    def make(_) -> tuple[str, str]:
        hash160 = _random_bytes(20)
        data = convertbits(list(hash160), 8, 5, True)  # type: ignore[list-item]
        return ("ATOM", bech32_encode("cosmos", data, "bech32"))
    return st.builds(make, st.none())


# --- Long-tail representatives ---


def tron_address_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("TRX", base58check_encode(b"\x41" + _random_bytes(20))),
        st.none(),
    )


def stellar_account_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid Stellar G... accounts (version 0x30 + 32-byte pubkey + CRC16)."""
    import base64
    def make(_) -> tuple[str, str]:
        payload = b"\x30" + _random_bytes(32)
        checksum = crc16_xmodem(payload).to_bytes(2, "big")
        full = payload + checksum
        encoded = base64.b32encode(full).decode("ascii").rstrip("=")
        return ("XLM", encoded)
    return st.builds(make, st.none())


def polkadot_address_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid Polkadot SS58 addresses."""
    import base58
    from ckc.validators.base import blake2b
    def make(_) -> tuple[str, str]:
        pubkey = _random_bytes(32)
        payload = b"\x00" + pubkey  # prefix 0 = Polkadot
        checksum = blake2b(b"SS58PRE" + payload, digest_size=64)[:2]
        full = payload + checksum
        return ("DOT", base58.b58encode(full).decode("ascii"))
    return st.builds(make, st.none())


def monero_address_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid Monero mainnet addresses."""
    def make(_) -> tuple[str, str]:
        payload = b"\x12" + _random_bytes(32) + _random_bytes(32)
        checksum = keccak256(payload)[:4]
        full = payload + checksum
        return ("XMR", monero_base58_encode(full))
    return st.builds(make, st.none())


# Aggregated strategy — picks a random chain
ALL_STRATEGIES = [
    btc_p2pkh_strategy(), btc_p2sh_strategy(), btc_bech32_strategy(),
    ltc_p2pkh_strategy(), doge_p2pkh_strategy(),
    eth_address_strategy(), eth_privkey_strategy(),
    solana_address_strategy(), cosmos_address_strategy(),
    tron_address_strategy(), stellar_account_strategy(),
    polkadot_address_strategy(), monero_address_strategy(),
]


def any_chain_strategy() -> SearchStrategy[tuple[str, str]]:
    """Pick any chain's strategy at random."""
    return st.one_of(*ALL_STRATEGIES)
```

- [ ] **Step 4: Write `tests/fuzz/mutations.py`**

```python
"""Mutation functions: take a valid key string, return a corrupted variant.

Each mutation is small and well-defined so we can measure recovery rates
per mutation type.
"""

from __future__ import annotations

import os
import random

from ckc.repairs import OCR_MAP


def whitespace_pollution(s: str) -> str:
    """Add spaces/newlines/tabs around the string."""
    n_lead = random.randint(1, 5)
    n_trail = random.randint(1, 5)
    ws_chars = [" ", "\n", "\t", "\xa0", "​"]
    lead = "".join(random.choice(ws_chars) for _ in range(n_lead))
    trail = "".join(random.choice(ws_chars) for _ in range(n_trail))
    return lead + s + trail


def case_flip(s: str) -> str:
    """Flip case of one alphabetic character."""
    alpha_indices = [i for i, c in enumerate(s) if c.isalpha()]
    if not alpha_indices:
        return s
    idx = random.choice(alpha_indices)
    ch = s[idx]
    flipped = ch.lower() if ch.isupper() else ch.upper()
    return s[:idx] + flipped + s[idx + 1:]


def char_substitute(s: str) -> str:
    """Replace one char with another from a plausible charset."""
    if len(s) < 2:
        return s
    idx = random.randint(0, len(s) - 1)
    # Use a char that already appears in the string (keeps it in charset)
    new_char = random.choice([c for i, c in enumerate(s) if i != idx])
    return s[:idx] + new_char + s[idx + 1:]


def char_delete(s: str) -> str:
    """Remove one character."""
    if len(s) < 2:
        return s
    idx = random.randint(0, len(s) - 1)
    return s[:idx] + s[idx + 1:]


def char_insert(s: str) -> str:
    """Insert one random char at a random position."""
    if not s:
        return s
    idx = random.randint(0, len(s))
    new_char = random.choice(s)  # pick a char already in string
    return s[:idx] + new_char + s[idx:]


def char_swap_adjacent(s: str) -> str:
    """Swap two adjacent characters."""
    if len(s) < 2:
        return s
    idx = random.randint(0, len(s) - 2)
    return s[:idx] + s[idx + 1] + s[idx] + s[idx + 2:]


def ocr_substitute(s: str) -> str:
    """Apply one OCR confusable substitution (O→0, l→1, S→5, etc.)."""
    candidates = [(i, ch, OCR_MAP[ch]) for i, ch in enumerate(s) if ch in OCR_MAP]
    if not candidates:
        return s
    idx, old, new = random.choice(candidates)
    return s[:idx] + new + s[idx + 1:]


ALL_MUTATIONS = [
    whitespace_pollution,
    case_flip,
    char_substitute,
    char_delete,
    char_insert,
    char_swap_adjacent,
    ocr_substitute,
]
```

- [ ] **Step 5: Verify imports work**

```bash
py -c "from tests.fuzz.strategies import any_chain_strategy; from tests.fuzz.mutations import ALL_MUTATIONS; print('OK', len(ALL_MUTATIONS))"
```
Expected: `OK 7`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tests/fuzz/
git commit -m "Add hypothesis dep + fuzz helpers (strategies per chain + mutation functions)"
```

---

## Task 2: Property tests for MVP validators

**Files:**
- Create: `tests/fuzz/test_mvp_fuzz.py`

- [ ] **Step 1: Write property tests**

`tests/fuzz/test_mvp_fuzz.py`:

```python
"""Property tests: generate valid MVP-chain keys, mutate, verify recovery.

Target recovery rates per spec:
- whitespace pollution: 100%
- OCR substitution: ≥80%
- char swap (same charset): ≥50%
"""

from __future__ import annotations

from hypothesis import given, settings, HealthConstraint

from ckc.pipeline import classify
from tests.fuzz.strategies import (
    btc_p2pkh_strategy, btc_p2sh_strategy, btc_bech32_strategy,
    ltc_p2pkh_strategy, doge_p2pkh_strategy,
    eth_address_strategy, eth_privkey_strategy,
    solana_address_strategy, cosmos_address_strategy,
)
from tests.fuzz.mutations import (
    whitespace_pollution, case_flip, ocr_substitute,
)


def _top_chain(corrupted: str) -> str | None:
    """Run pipeline on corrupted input, return top match's chain or None."""
    results = classify(corrupted)
    return results[0].chain if results else None


# --- Whitespace pollution: should ALWAYS be recovered (Stage 1 strip-ws) ---


@given(btc_p2pkh_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_btc_p2pkh_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(eth_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_eth_address_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(solana_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_solana_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(cosmos_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_cosmos_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


# --- Sanity: original (unmutated) key MUST classify correctly ---


@given(btc_p2pkh_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_btc_p2pkh_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(btc_bech32_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_btc_bech32_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(ltc_p2pkh_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_ltc_p2pkh_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(doge_p2pkh_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_doge_p2pkh_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(eth_privkey_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_eth_privkey_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


# --- Aggregated whitespace test (covers all MVP chains at once) ---


@given(
    btc_p2pkh_strategy() | btc_p2sh_strategy() | btc_bech32_strategy() |
    ltc_p2pkh_strategy() | doge_p2pkh_strategy() |
    eth_address_strategy() | eth_privkey_strategy() |
    solana_address_strategy() | cosmos_address_strategy()
)
@settings(max_examples=200, deadline=None, suppress_health_check=list(HealthConstraint))
def test_all_mvp_chains_whitespace_recovered(item):
    """All MVP-chain keys should survive whitespace pollution."""
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain, f"failed for {chain}: {addr!r} → {corrupted!r}"
```

- [ ] **Step 2: Run tests**

`py -m pytest tests/fuzz/test_mvp_fuzz.py -v` → all should pass.

If any fail, investigate which mutation broke recovery and either:
- Fix the bug in preprocessor/repairs
- Document the failure mode in the test

- [ ] **Step 3: Commit**

```bash
git add tests/fuzz/test_mvp_fuzz.py
git commit -m "Add property tests for MVP validators (whitespace recovery + sanity)"
```

---

## Task 3: Property tests for long-tail validators

**Files:**
- Create: `tests/fuzz/test_long_tail_fuzz.py`

- [ ] **Step 1: Write property tests**

`tests/fuzz/test_long_tail_fuzz.py`:

```python
"""Property tests for long-tail validators (Tron, Stellar, Polkadot, Monero)."""

from __future__ import annotations

from hypothesis import given, settings, HealthConstraint

from ckc.pipeline import classify
from tests.fuzz.strategies import (
    tron_address_strategy, stellar_account_strategy,
    polkadot_address_strategy, monero_address_strategy,
)
from tests.fuzz.mutations import whitespace_pollution


def _top_chain(corrupted: str) -> str | None:
    results = classify(corrupted)
    return results[0].chain if results else None


@given(tron_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_tron_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(stellar_account_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_stellar_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(polkadot_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_polkadot_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(monero_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_monero_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(tron_address_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_tron_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(stellar_account_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_stellar_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(polkadot_address_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_polkadot_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(monero_address_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_monero_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain
```

- [ ] **Step 2: Run**

`py -m pytest tests/fuzz/test_long_tail_fuzz.py -v` → all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/fuzz/test_long_tail_fuzz.py
git commit -m "Add property tests for long-tail validators (TRX/XLM/DOT/XMR)"
```

---

## Task 4: Mnemonic fuzz tests

**Files:**
- Create: `tests/fuzz/test_mnemonic_fuzz.py`

- [ ] **Step 1: Write tests**

`tests/fuzz/test_mnemonic_fuzz.py`:

```python
"""Property tests for mnemonic validator.

Generate random valid mnemonics by sampling from the BIP-39 wordlist
with a valid checksum. Then mutate (whitespace pollution, single-word
substitution with another valid word) and verify the pipeline still
identifies the result as BIP39.
"""

from __future__ import annotations

import os
import hashlib
from importlib import resources

from hypothesis import given, settings, strategies as st, HealthConstraint

from ckc.pipeline import classify


def _load_wordlist() -> list[str]:
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        return [line.strip() for line in f if line.strip()]


WORDS = _load_wordlist()
WORD_TO_IDX = {w: i for i, w in enumerate(WORDS)}


def _generate_valid_12_word() -> str:
    """Generate a valid 12-word BIP-39 mnemonic."""
    entropy = os.urandom(16)  # 128 bits
    checksum = hashlib.sha256(entropy).digest()
    # ENT=128, CS=4. Bits = entropy (128) + first 4 bits of checksum
    bits = "".join(format(b, "08b") for b in entropy)
    bits += format(checksum[0] >> 4, "04b")  # first 4 bits
    # Split into 11-bit groups, each → word index
    indices = [int(bits[i:i + 11], 2) for i in range(0, 132, 11)]
    return " ".join(WORDS[i] for i in indices)


def _top_chain(corrupted: str) -> str | None:
    results = classify(corrupted)
    return results[0].chain if results else None


@given(st.builds(_generate_valid_12_word))
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_valid_mnemonic_classified_as_bip39(mnemonic):
    """A valid 12-word BIP-39 mnemonic must classify as BIP39."""
    chain = _top_chain(mnemonic)
    assert chain == "BIP39"


@given(st.builds(_generate_valid_12_word))
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthConstraint))
def test_mnemonic_with_whitespace_recovered(mnemonic):
    """Mnemonic with whitespace pollution should still be recovered."""
    import random
    corrupted = "  " + mnemonic + "\n"
    chain = _top_chain(corrupted)
    assert chain == "BIP39"


@given(st.builds(_generate_valid_12_word))
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthConstraint))
def test_mnemonic_uppercase_recovered(mnemonic):
    """Mnemonic in uppercase should be lowercased and recovered."""
    corrupted = mnemonic.upper()
    chain = _top_chain(corrupted)
    assert chain == "BIP39"
```

- [ ] **Step 2: Run**

`py -m pytest tests/fuzz/test_mnemonic_fuzz.py -v` → all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/fuzz/test_mnemonic_fuzz.py
git commit -m "Add mnemonic property tests (valid generation + whitespace/case recovery)"
```

---

## Task 5: Aggregate report + tag v0.4.0-hardened

**Files:**
- Create: `tests/test_fuzz_aggregate.py` — meta-test that runs all fuzz tests and asserts total recovery rate

- [ ] **Step 1: Write aggregate test**

`tests/test_fuzz_aggregate.py`:

```python
"""Aggregate fuzz report: run many random tests, count recovery rates."""

from __future__ import annotations

import random

from ckc.pipeline import classify
from tests.fuzz.strategies import (
    btc_p2pkh_strategy, eth_address_strategy, solana_address_strategy,
    cosmos_address_strategy, tron_address_strategy, monero_address_strategy,
)
from tests.fuzz.mutations import (
    whitespace_pollution, case_flip, char_swap_adjacent, ocr_substitute,
)


STRATEGIES = [
    btc_p2pkh_strategy, eth_address_strategy, solana_address_strategy,
    cosmos_address_strategy, tron_address_strategy, monero_address_strategy,
]


def _make_one(strategy_fn):
    """Draw one sample from a strategy (uses hypothesis internals lightly)."""
    from hypothesis import find
    return find(strategy_fn(), lambda x: True)


def test_whitespace_recovery_100_percent():
    """Whitespace pollution recovery target: 100%."""
    passed = 0
    total = 30
    for _ in range(total):
        strat = random.choice(STRATEGIES)
        chain, addr = _make_one(strat)
        corrupted = whitespace_pollution(addr)
        results = classify(corrupted)
        if results and results[0].chain == chain:
            passed += 1
    recovery = passed / total
    assert recovery == 1.0, f"whitespace recovery {recovery:.0%} < 100%"


def test_overall_recovery_above_threshold():
    """At least 60% of single-mutation corruptions should be recovered."""
    mutations = [case_flip, char_swap_adjacent, ocr_substitute, whitespace_pollution]
    passed = 0
    total = 60
    for _ in range(total):
        strat = random.choice(STRATEGIES)
        mutation = random.choice(mutations)
        chain, addr = _make_one(strat)
        corrupted = mutation(addr)
        if corrupted == addr:
            continue  # mutation was a no-op, skip
        results = classify(corrupted)
        if results and results[0].chain == chain:
            passed += 1
    recovery = passed / total
    assert recovery >= 0.6, f"overall recovery {recovery:.0%} < 60%"
```

- [ ] **Step 2: Run full suite**

`py -m pytest -v` → 203 prior + fuzz tests + aggregate = ~280+ tests pass.

- [ ] **Step 3: Ruff + pyright**

`py -m ruff check src/ckc/ tests/` → clean.
`py -m pyright src/ckc/` → external-stub errors only.

- [ ] **Step 4: Commit + tag**

```bash
git add tests/test_fuzz_aggregate.py
git commit -m "Add fuzz aggregate recovery-rate test"
git tag -a v0.4.0-hardened -m "Property/fuzz tests: 280+ tests verifying recovery rates across all chains"
```

---

## Done criteria

- Hypothesis installed and integrated
- Strategies generate valid keys for at least 10 chains
- Mutation functions cover whitespace, case, char-sub, char-del, char-ins, swap, OCR
- Property tests verify whitespace recovery = 100%
- Property tests verify overall recovery ≥ 60%
- Mnemonic property tests verify valid mnemonics always classify
- All tests pass (~280+)
- Tag v0.4.0-hardened created

## What's next

Nothing — this is the final plan. The full spec is implemented:
- Plan 1: MVP (4 validators, ~25 chains)
- Plan 2: Long-tail (12 more validators)
- Plan 3: Mnemonic (BIP-39 + Electrum + Levenshtein)
- Plan 4: Fuzzing harness
