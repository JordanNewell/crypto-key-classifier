# Crypto Key Classifier — Long-Tail Validators Plan (Plan 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend coverage from 4 validators (~25 chains) to 16 validators (~40 chains) by adding Monero, Cardano, Tezos, Polkadot, TON, Stellar, Tron, Algorand, Kaspa, Sui/Aptos, Near, Ripple.

**Architecture:** Same validator-per-chain pattern as MVP. Each new validator lives in `src/ckc/validators/<chain>.py`, auto-discovered by the registry. Some validators need new shared helpers (Blake2b, CRC16-XMODEM, SHA512/256, Monero block-base58) which land in `base.py`.

**Tech Stack:** Same as MVP (Python 3.10+, base58, pycryptodome). Adds stdlib `hashlib.blake2b` and a small CRC16-XMODEM impl.

**Reference:** `docs/superpowers/specs/2026-07-12-crypto-key-classifier-design.md` (chain specs locked in there).

---

## File structure

```
crypto-key-classifier/
├── src/ckc/
│   ├── validators/
│   │   ├── base.py                    # Task 1 — add helpers (crc16_xmodem, blake2b, sha512_256, monero_base58)
│   │   ├── tron.py                    # Task 2
│   │   ├── ripple.py                  # Task 3
│   │   ├── algorand.py                # Task 4
│   │   ├── tezos.py                   # Task 5
│   │   ├── polkadot.py                # Task 6
│   │   ├── stellar.py                 # Task 7
│   │   ├── ton.py                     # Task 8
│   │   ├── cardano.py                 # Task 9
│   │   ├── monero.py                  # Task 10
│   │   ├── kaspa.py                   # Task 11
│   │   ├── sui_aptos.py               # Task 12
│   │   └── near.py                    # Task 13
│   └── data/
│       └── wallets.py                 # Task 1 — extend WALLETS dict with 13 new chains
└── tests/
    ├── validators/
    │   ├── test_tron.py               # Task 2
    │   ├── test_ripple.py             # Task 3
    │   ├── test_algorand.py           # Task 4
    │   ├── test_tezos.py              # Task 5
    │   ├── test_polkadot.py           # Task 6
    │   ├── test_stellar.py            # Task 7
    │   ├── test_ton.py                # Task 8
    │   ├── test_cardano.py            # Task 9
    │   ├── test_monero.py             # Task 10
    │   ├── test_kaspa.py              # Task 11
    │   ├── test_sui_aptos.py          # Task 12
    │   └── test_near.py               # Task 13
    ├── fixtures/
    │   └── <chain>_vectors.json       # one per validator
    └── test_long_tail_e2e.py          # Task 14
```

---

## Chain specs (reference — locked in spec)

| Chain | Format summary | Checksum |
|-------|----------------|----------|
| **Tron (TRX)** | `0x41` + 20-byte Keccak hash + 4-byte checksum → base58check, 34 chars, always `T...` | Double-SHA256 (use existing `base58check`) |
| **Ripple (XRP)** | `0x00` + 20-byte hash + 4-byte checksum → base58check, always `r...` (XRP alphabet differs from BTC: `rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz`) | Double-SHA256 |
| **Algorand (ALGO)** | 32-byte Ed25519 pubkey + 4-byte SHA512/256 checksum → base32 RFC4648 unpadded → exactly 58 chars | SHA512/256 (NIST variant, first 4 bytes) |
| **Tezos (XTZ)** | 3-byte prefix + 20-byte Blake2b PKH + 4-byte checksum → base58check, 36 chars. tz1=Ed25519, tz2=secp256k1, tz3=P-256, tz4=BLS12-381 | Double-SHA256 (use existing) |
| **Polkadot (DOT/KSM)** | SS58: prefix byte + pubkey + N-byte Blake2b-512("SS58PRE" + payload) checksum → base58, where N depends on payload length (≤32B→2B, 33-37B→3B, ≥38B→4B) | Blake2b-512 with "SS58PRE" domain sep |
| **Stellar (XLM)** | version byte (`0x30`=`G` account, `0x90`=`S` secret, `0x60`=`M` muxed) + payload + 2-byte CRC16-XMODEM → base32 RFC4648 unpadded, 56 chars (G/S) or 69 (M) | CRC16-XMODEM |
| **TON** | tag(1: `0x11` bounceable, `0x51` non-bounceable, `0x80` testnet OR) + workchain(1) + 32-byte hash + 2-byte CRC16-XMODEM → base64/url, `EQ`/`UQ`/`kQ`/`0Q` prefixes | CRC16-XMODEM |
| **Cardano (ADA)** | bech32 with `addr1`/`stake1`/`addr_test1` HRPs, OR Byron legacy base58 (`DdzFFz...`) | bech32 checksum (have) |
| **Monero (XMR)** | 1-byte network (`0x12` mainnet) + 32-byte spend pubkey + 32-byte view pubkey + 4-byte Keccak checksum → BLOCK-ENCODED base58 (8-byte blocks → 11 chars), 95 chars mainnet | Keccak-256 (first 4 bytes) |
| **Kaspa (KAS)** | bech32 with `kaspa` (mainnet) / `kaspatest` HRP. Body = Schnorr pubkey | bech32 (have) |
| **Sui / Aptos** | `0x` + 64 hex (32-byte). Sui = BLAKE2b of pubkey; Aptos = SHA3-256. **Ambiguous** — flag both as candidates. | None |
| **Near (NEAR)** | Implicit: 64 lowercase hex (32-byte Ed25519, no `0x`). Named: regex `^[a-z0-9-]+\.near$` (low-value, mostly skip). | None for implicit |

---

## Task 1: Shared helpers + wallet DB extension

**Files:**
- Modify: `src/ckc/validators/base.py`
- Modify: `src/ckc/data/wallets.py`
- Create: `tests/test_helpers.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_helpers.py
from ckc.validators.base import (
    crc16_xmodem, blake2b, sha512_256, monero_base58_encode, monero_base58_decode,
)
from ckc.data.wallets import wallets_for


def test_crc16_xmodem_known_vector():
    # CRC16-XMODEM of b"123456789" is 0x31C3
    assert crc16_xmodem(b"123456789") == 0x31C3


def test_blake2b_known_vector():
    # BLAKE2b-256 of empty string
    expected = bytes.fromhex("0e5751c026e543b2e8ab2eb06099daa1d1e5df47778f7787faab45cdf12fe3a8")
    assert blake2b(b"", digest_size=32) == expected


def test_sha512_256_known_vector():
    # SHA512/256 of empty string (NIST variant, NOT SHA-512 truncated)
    expected = bytes.fromhex("c672b8d1ef56ed28ab87c3622c5114069bdd3ad7b8f9737498d0c01ecef0967a")
    assert sha512_256(b"") == expected


def test_monero_base58_round_trip():
    # 8-byte blocks → 11 chars each, last block carries remainder
    raw = bytes(range(66))  # 8 blocks of 8 bytes + 2 bytes remainder
    encoded = monero_base58_encode(raw)
    decoded = monero_base58_decode(encoded)
    assert decoded == raw


def test_monero_base58_block_boundary():
    # Encode a known Monero-shaped payload (network + 32 + 32 + checksum = 69 bytes)
    payload = b"\x12" + b"\x00" * 32 + b"\x01" * 32 + b"\xff" * 4
    encoded = monero_base58_encode(payload)
    assert len(encoded) == 95  # Monero mainnet address length
    decoded = monero_base58_decode(encoded)
    assert decoded == payload


def test_wallets_extended():
    # 13 new chains must be in the DB
    for chain in ["XMR", "ADA", "XRP", "XLM", "TRX", "XTZ", "DOT", "TON", "ALGO", "KAS", "SUI", "APT", "NEAR"]:
        assert wallets_for(chain), f"missing wallet list for {chain}"
```

- [ ] **Step 2: Verify failure**

`py -m pytest tests/test_helpers.py -v` → FAIL with ImportError.

- [ ] **Step 3: Add helpers to `src/ckc/validators/base.py`**

Append to existing base.py (do NOT remove anything):

```python
# --- Additional helpers for long-tail chains (Plan 2) ---

import hashlib
import base64


def crc16_xmodem(data: bytes) -> int:
    """CRC16-XMODEM (used by Stellar, TON). Polynomial 0x1021, init 0x0000."""
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def blake2b(data: bytes, digest_size: int = 32) -> bytes:
    """BLAKE2b hash with configurable digest size."""
    return hashlib.blake2b(data, digest_size=digest_size).digest()


def sha512_256(data: bytes) -> bytes:
    """SHA-512/256 (NIST variant, used by Algorand). NOT truncated SHA-512."""
    return hashlib.new("sha512_256", data).digest()


# --- Monero block-encoded base58 ---
# Monero uses 8-byte blocks → 11 chars each, with the LAST block carrying
# any remainder bytes (NOT whole-payload like Bitcoin base58check).

_MONERO_BLOCK_SIZES = [
    (0, 0), (2, 1), (3, 2), (5, 3), (6, 4), (7, 5), (9, 6), (10, 7), (12, 8)
]
_MONERO_ENCODED_BLOCK_SIZES = [0, 2, 3, 5, 6, 7, 9, 10, 11]

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_INDEX = {c: i for i, c in enumerate(_BASE58_ALPHABET)}


def _monero_encode_block(data: bytes, from_index: int) -> tuple[str, int]:
    """Encode a single block, return (encoded_chars, next_index)."""
    # Find block size
    for full_block_size, encoded_size in [(8, 11)] + [
        (sz, esz) for sz, esz in _MONERO_BLOCK_SIZES if sz < 8
    ]:
        pass
    # Simpler: pick the right block size based on remaining bytes
    remaining = len(data) - from_index
    if remaining >= 8:
        block_size = 8
        encoded_size = 11
    else:
        # Use lookup
        block_size, encoded_size = _MONERO_BLOCK_SIZES[remaining]

    block = data[from_index:from_index + block_size]
    # Convert bytes to integer (big-endian), then to base58
    num = int.from_bytes(block, "big") if block else 0
    chars = []
    for _ in range(encoded_size):
        num, rem = divmod(num, 58)
        chars.append(_BASE58_ALPHABET[rem])
    # Reverse because we built it least-significant-first
    return "".join(reversed(chars)), from_index + block_size


def _monero_decode_block(text: str) -> tuple[bytes, int]:
    """Decode a single block, return (bytes, chars_consumed)."""
    # Pick encoded_size based on input length boundaries (heuristic per spec)
    # This is complex — use a simpler approach: try to decode based on input length
    raise NotImplementedError("Use monero_base58_decode instead")


def monero_base58_encode(data: bytes) -> str:
    """Encode bytes using Monero's block-encoded base58 (8-byte → 11-char blocks)."""
    result = []
    i = 0
    while i < len(data):
        encoded, i = _monero_encode_block(data, i)
        result.append(encoded)
    return "".join(result)


def monero_base58_decode(s: str) -> bytes:
    """Decode Monero's block-encoded base58."""
    # Calculate how many full 11-char blocks + remainder
    full_blocks = len(s) // 11
    remainder_chars = len(s) % 11
    # Reverse-lookup remainder
    remainder_bytes = 0
    for rbs, ebs in _MONERO_BLOCK_SIZES:
        if ebs == remainder_chars:
            remainder_bytes = rbs
            break

    result = b""
    pos = 0
    for _ in range(full_blocks):
        block_str = s[pos:pos + 11]
        pos += 11
        num = 0
        for ch in block_str:
            if ch not in _BASE58_INDEX:
                raise ValueError(f"invalid char {ch!r}")
            num = num * 58 + _BASE58_INDEX[ch]
        result += num.to_bytes(8, "big")

    if remainder_chars:
        block_str = s[pos:pos + remainder_chars]
        num = 0
        for ch in block_str:
            if ch not in _BASE58_INDEX:
                raise ValueError(f"invalid char {ch!r}")
            num = num * 58 + _BASE58_INDEX[ch]
        result += num.to_bytes(remainder_bytes, "big")

    return result
```

**IMPORTANT — the `_monero_encode_block` function above is buggy** (the loop at the top is dead code). Use this corrected version:

```python
def _monero_encode_block(data: bytes, from_index: int) -> tuple[str, int]:
    """Encode a single block, return (encoded_chars, next_index)."""
    remaining = len(data) - from_index
    if remaining >= 8:
        block_size = 8
        encoded_size = 11
    else:
        # Find matching block size from the lookup table
        block_size, encoded_size = _MONERO_BLOCK_SIZES[remaining]

    block = data[from_index:from_index + block_size]
    num = int.from_bytes(block, "big") if block else 0
    chars = []
    for _ in range(encoded_size):
        num, rem = divmod(num, 58)
        chars.append(_BASE58_ALPHABET[rem])
    return "".join(reversed(chars)), from_index + block_size
```

- [ ] **Step 4: Extend `src/ckc/data/wallets.py`**

Add these entries to the WALLETS dict:

```python
    # Long-tail chains (Plan 2)
    "XMR": ["Monero GUI Wallet", "Cake Wallet", "Monerujo", "Ledger"],
    "ADA": ["Daedalus", "Yoroi", "AdaLite", "Ledger", "Trezor"],
    "XRP": ["Xumm", "Ledger", "Trezor", "GateHub"],
    "XLM": ["Freighter", "Lobstr", "Ledger"],
    "TRX": ["TronLink", "Ledger", "Trezor"],
    "XTZ": ["Temple", "Kukai", "Ledger"],
    "DOT": ["Polkadot.js", "Ledger", "Trezor"],
    "KSM": ["Polkadot.js", "Ledger"],
    "TON": ["Tonkeeper", "MyTonWallet", "Ledger"],
    "ALGO": ["Pera Wallet", "Ledger"],
    "KAS": ["Kaspa Wallet", "Ledger"],
    "SUI": ["Sui Wallet", "Ledger"],
    "APT": ["Petra Wallet", "Ledger"],
    "NEAR": ["Near Wallet", "Ledger"],
```

- [ ] **Step 5: Verify all tests pass**

`py -m pytest tests/test_helpers.py -v` → 6 passed.
`py -m pytest -v` → all prior + 6 new passed.

- [ ] **Step 6: Commit**

```bash
git add src/ckc/validators/base.py src/ckc/data/wallets.py tests/test_helpers.py
git commit -m "Add helpers for long-tail chains (CRC16-XMODEM, Blake2b, SHA512/256, Monero base58) + extend wallet DB"
```

---

## Tasks 2–13: One per validator

Each task follows the same shape:

1. Write `tests/fixtures/<chain>_vectors.json` (generated-fixture documentation)
2. Write `tests/validators/test_<chain>.py` using `base58check_encode` / `bech32_encode` / chain-specific encoder to generate known-valid fixtures
3. Run failing test
4. Implement `src/ckc/validators/<chain>.py`
5. Run passing test
6. Commit

### Validator implementation patterns (reference for implementer)

**Simple base58check chains (Tron, Ripple, Tezos):** same pattern as BTC validator. Use existing `base58check_encode`/`base58check_decode`. For Ripple, use a custom base58 alphabet. For Tezos, dispatch on tz1/tz2/tz3/tz4 prefix bytes.

**bech32 chains (Cardano, Kaspa):** use existing `bech32_decode`/`bech32_encode`. Cardano cross-chain via HRP not applicable (each HRP is a different chain concept). Kaspa is single-HRP.

**Monero (complex):** use new `monero_base58_encode`/`monero_base58_decode` + Keccak for checksum. Length 95 chars mainnet.

**Polkadot (complex):** use base58 + Blake2b-512("SS58PRE" + payload) checksum with variable length.

**Stellar/TON (CRC16):** use existing base32 (stdlib `base64.b32decode` with removal of padding) / base64, plus new `crc16_xmodem` helper.

**Algorand:** use base32 stdlib, plus new `sha512_256` helper.

**Sui/Aptos:** same shape as ETH but 64 hex (32 bytes) vs 40 hex (20 bytes). Flag as ambiguous between SUI and APT.

**Near:** implicit = 64 hex ed25519, named = regex.

### Per-task test contract

Each validator test must:
- Generate at least one known-valid fixture programmatically (encode-then-decode)
- Test valid input returns Match with correct chain + format
- Test invalid input returns None
- Test shape_match positive/negative cases
- Test cross_chain_alternates populated when applicable (most don't have any)

### Per-task commit message format

`Add <Chain> validator (<short description>)`

---

## Task 14: Pipeline update + e2e + tag

**Files:**
- Modify: `src/ckc/pipeline.py` (update `_validator_chain_codes`)
- Create: `tests/test_long_tail_e2e.py`

- [ ] **Step 1: Update `_validator_chain_codes`** in `pipeline.py` to include new validators' chain codes:

```python
def _validator_chain_codes(validator) -> set[str]:
    chain = getattr(validator, "chain", "")
    if chain == "BTC_FAMILY":
        return {"BTC", "LTC", "DOGE", "BCH"}
    if chain == "COSMOS_FAMILY":
        return {chain for chain, _ in _HRPS}  # or list them
    if chain == "ETH":
        return {"ETH", "POLYGON", "ARBITRUM", "BASE", "OPTIMISM", "BSC", "AVALANCHE"}
    if chain == "SOL":
        return {"SOL"}
    # New long-tail validators — each returns a singleton (or specific set)
    # Use class attribute `chains_covered` if defined, else fall back to {chain}
    chains_covered = getattr(validator, "chains_covered", None)
    if chains_covered:
        return set(chains_covered)
    return {chain}
```

- [ ] **Step 2: Write E2E test** covering each new validator with a generated fixture.

- [ ] **Step 3: Run full suite** (`py -m pytest -v`) — all tests must pass (65 prior + 12 new validator tests + helpers + e2e ≈ 100+).

- [ ] **Step 4: Ruff + pyright** — ruff must be clean, pyright external-stub errors only.

- [ ] **Step 5: Manual smoke** — exercise each new validator from CLI.

- [ ] **Step 6: Commit + tag**

```bash
git add src/ckc/pipeline.py tests/test_long_tail_e2e.py
git commit -m "Update pipeline chain codes + add long-tail e2e tests"
git tag -a v0.2.0-long-tail -m "Long-tail validators: 12 new chains (XMR/ADA/XTZ/DOT/TON/XLM/TRX/ALGO/KAS/SUI/APT/NEAR/XRP)"
```

---

## Done criteria

- 12 new validators all ship
- All tests pass
- Ruff clean
- Manual smoke from CLI produces sensible output for each chain
- Tag `v0.2.0-long-tail` created

## What's next

- **Plan 3:** Mnemonic validator (BIP39 + Electrum + Levenshtein wordlist repair)
- **Plan 4:** Property tests + fuzzing harness
