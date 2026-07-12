# Crypto Key Classifier — Design Spec

**Date:** 2026-07-12
**Status:** Draft (awaiting Jordan review)
**Author:** Claude (brainstormed with Jordan, S342)
**Related:** None (greenfield project)

---

## Context & Motivation

Jordan has an unknown folder of mystery strings — could be BTC addresses, ETH keys, SOL addresses, mnemonics, anything. They want a tool that takes any random string and confidently identifies what kind of crypto key it is, which wallet software would import it, and what alternate chains it could be re-used on. The tool must recover from common corruptions (whitespace, bad checksums, encoding mismatches, OCR errors) — strict regex matching isn't enough.

**Survey of existing tools (research, 2026-07-12):** TruffleHog, Gitleaks, detect-secrets, GitHub Secret Scanning are all strict pattern-matchers. None do fuzzy recovery, OCR repair, encoding conversion, or wallet-compatibility recommendations. The Cosmos / BTC-fork / Polkadot cross-chain re-encoding feature is particularly novel — no surveyed tool offers it.

This is a greenfield tool. No prior implementation exists in Jordan's projects (verified by search of `E:/dev/projects/`, Claude session logs, file-history, vaults, and VSCode workspace storage — a stale reference to a deleted `D:/dev/projects/crypto/solana-projects/Solana` folder was found but the folder is gone).

## Goals

1. **Classify any plausible crypto-key string** across 15+ chains (BTC, ETH, SOL, XMR, ADA, XRP, XLM, TRX, XTZ, DOT, NEAR, SUI, APT, TON, ALGO, KAS, + BTC forks LTC/DOGE/BCH, + EVM L2s, + Cosmos IBC family, + Polkadot relay chains, + BIP39/Electrum mnemonics).
2. **Recover from corruption** — formatting noise, failed checksums (typos), wrong encoding, OCR mangling, partial/redacted input.
3. **Recommend wallet software** for each match — MetaMask, Phantom, Bitcoin Core, Electrum, Keplr, etc.
4. **Cross-chain expansion** — for shared-key families (Cosmos IBC, BTC forks, Polkadot networks), enumerate the alternate encodings directly so the user can copy-paste.
5. **Batch mode** — terse one-line-per-input output for piping, with auto-detection of single vs batch input.
6. **Privacy-safe** — masks private keys by default, zero network calls, no telemetry, no real keys in test fixtures.

## Non-goals

- **Hedera (HBAR)** — account IDs only, no key format. Out of scope.
- **Live wallet verification** (TruffleHog-style API calls) — out of scope, violates local-only preference.
- **Key generation, signing, transaction broadcast** — this is a classifier, not a wallet.
- **Named accounts** (e.g. `alice.near`, ENS names) — too unreliable to classify as keys. Hex/encoded forms only.

---

## Architecture (Approach A — Validator-per-chain + shared repair pipeline)

```
raw input (string | iterable)
  │
  ▼
preprocessor ──► normalized string + metadata
  │
  ▼
candidate generator ──► [candidate_variants]  (whitespace-stripped, OCR-fixed, re-encoded…)
  │
  ▼
validator registry ──► fan out to all enabled validators (auto-discovered)
  │
  ▼
each validator: shape-match? → strict validate → if fail, request repairs → re-validate → score
  │
  ▼
collect + rank by confidence
  │
  ▼
reporter (rich / terse / json)
```

**Design principles:**
- One validator class per chain (or per chain family — BTC forks grouped, EVM L2s grouped).
- Validators are auto-discovered; dropping a new `validators/foo.py` extends the pipeline with no central registration.
- Repairs are composable primitives, not embedded in validators. Validators say "I need 32 bytes"; the repair layer tries encodings/OCR/substitutions to produce 32 bytes.
- "Break on first valid": once any candidate validates with checksum pass, pipeline stops repairing that input.

## Project layout

```
E:/dev/projects/crypto-key-classifier/
├── pyproject.toml
├── README.md
├── src/ckc/
│   ├── __init__.py
│   ├── cli.py                  # argparse entry, dispatches modes
│   ├── pipeline.py             # orchestrator
│   ├── preprocessor.py         # normalization + candidate generation
│   ├── reporter.py             # output rendering (rich/terse/json)
│   ├── models.py               # Candidate, Match dataclasses
│   ├── repairs.py              # repair primitives (whitespace, OCR, encoding)
│   └── validators/
│       ├── __init__.py         # registry, auto-discovery
│       ├── base.py             # Validator protocol + shared helpers (base58check, bech32, etc.)
│       ├── btc.py              # BTC, LTC, DOGE, BCH (shared key, different version bytes)
│       ├── evm.py              # ETH + all EVM L2s (shared 0x+40hex format)
│       ├── solana.py           # ed25519 base58
│       ├── monero.py           # block-encoded base58, Keccak checksum
│       ├── cardano.py          # bech32 addr1/stake1 + Byron legacy
│       ├── ripple.py
│       ├── stellar.py          # base32, CRC16-XMODEM, G/S/M
│       ├── tron.py             # base58check 0x41 prefix
│       ├── cosmos.py           # bech32, ~20 IBC chain HRPs
│       ├── tezos.py            # base58check tz1/2/3/4
│       ├── polkadot.py         # SS58, multi-network
│       ├── near.py             # implicit (64 hex) + named
│       ├── sui_aptos.py        # 0x+64 hex, flagged ambiguous
│       ├── ton.py              # base64, bounceable/non-bounceable
│       ├── algorand.py         # base32, 58 chars
│       ├── kaspa.py            # bech32 kaspa:
│       └── mnemonic.py         # BIP39 + Electrum detection
└── tests/
    ├── conftest.py
    ├── test_preprocessor.py
    ├── test_repairs.py
    ├── test_pipeline.py
    ├── test_reporter.py
    ├── fixtures/               # public test vectors only
    │   ├── btc_vectors.json
    │   ├── evm_vectors.json
    │   ├── solana_vectors.json
    │   └── ... (one per validator)
    └── validators/
        └── test_*.py           # one per validator
```

---

## Data models

```python
# src/ckc/models.py

@dataclass
class Candidate:
    raw: str                       # original input as received
    normalized: str                # after preprocessing
    repairs: list[str]             # e.g. ["strip-ws", "ocr:0→O"]
    encoding: str | None           # "base58" | "hex" | "bech32" | "base32" | ...
    bytes_value: bytes | None      # decoded form if any

@dataclass
class Match:
    chain: str                     # "BTC" | "ETH" | "SOL" | ...
    format: str                    # "P2PKH" | "P2SH" | "bech32-segwit" | "WIF" | ...
    key_type: str                  # "address" | "private-key" | "public-key" | "mnemonic"
    confidence: int                # 0-100, per tiers below
    checksum_status: str           # "valid" | "failed" | "none" | "skipped"
    network: str | None            # "mainnet" | "testnet" | "regtest"
    cross_chain_alternates: list[tuple[str, str]]  # [("OSMO", "osmo1..."), ...]
    wallet_compatibility: list[str]
    repairs_applied: list[str]
    notes: list[str]               # "Electrum seed (not BIP39)", "testnet", etc.
```

## Validator interface

```python
# src/ckc/validators/base.py

class Validator(Protocol):
    chain: str                     # canonical chain code
    formats: list[str]             # formats this validator handles

    def shape_match(self, candidate: Candidate) -> bool:
        """Cheap check: right length, charset, prefix? No checksum yet."""
        ...

    def validate(self, candidate: Candidate) -> Match | None:
        """Strict validation: checksum, network byte, etc. Returns None if rejected."""
        ...

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        """Return repair variants specific to this format (or [] to defer to generic layer)."""
        ...

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        """For formats with shared key/variant prefix (BTC forks, Cosmos, Polkadot)."""
        ...
```

## Pipeline orchestration

```python
# src/ckc/pipeline.py (pseudo)

def classify(raw: str, config: Config) -> list[Match]:
    base_candidates = preprocessor.generate(raw)   # ~3-10 variants
    matches = []
    for validator in registry.all():
        if config.chains and validator.chain not in config.chains:
            continue
        candidates = base_candidates + validator.suggest_repairs(base_candidates[0])
        for cand in candidates:
            if validator.shape_match(cand):
                m = validator.validate(cand)
                if m:
                    if m.confidence >= config.min_confidence:
                        m.cross_chain_alternates = validator.cross_chain_encodings(m)
                        matches.append(m)
                    if m.checksum_status == "valid":
                        break  # stop repairing once checksum passes
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches
```

---

## Chain coverage

17 validators covering ~30+ chains via cross-chain expansion:

| Validator | Chains covered | Shared-key note |
|-----------|----------------|-----------------|
| `btc.py` | BTC, LTC, DOGE, BCH | Same base58check + WIF; cross-encodings via version byte swap |
| `evm.py` | ETH + 20+ EVM L2s | Identical `0x`+40hex; cross-encodings are chain-ID-only (same address) |
| `solana.py` | SOL | ed25519 base58, no checksum (confidence caps at 50) |
| `monero.py` | XMR | Block-encoded base58 (8-byte→11-char blocks), Keccak-256 checksum |
| `cardano.py` | ADA | bech32 (`addr1`/`stake1`/`addr_test1`) + Byron legacy base58 (`DdzFFz`) |
| `ripple.py` | XRP | base58check `r`-prefix |
| `stellar.py` | XLM | base32 rfc4648 unpadded, CRC16-XMODEM, `G` (account) / `S` (secret) / `M` (muxed) |
| `tron.py` | TRX | base58check `0x41` prefix, always `T...` |
| `cosmos.py` | ATOM, OSMO, JUNO, AKT, INJ, +20 IBC chains | **One decode → 40+ re-encodings via HRP swap** |
| `tezos.py` | XTZ | base58check `tz1/2/3/4` (4 curves: Ed25519, secp256k1, P-256, BLS12-381) |
| `polkadot.py` | DOT, KSM, +relay chains | SS58, same key + different prefix byte |
| `near.py` | NEAR | Implicit (64 hex ed25519, no `0x`) + named accounts |
| `sui_aptos.py` | SUI, APT | `0x` + 64 hex; **flagged ambiguous** (same shape, different address hash algo) |
| `ton.py` | TON | base64/base64url, bounceable (`EQ`/`UQ`) / non-bounceable / testnet |
| `algorand.py` | ALGO | base32 rfc4648 unpadded, exactly 58 chars, SHA512/256 checksum |
| `kaspa.py` | KAS | bech32 `kaspa:` |
| `mnemonic.py` | BIP39 + Electrum (all chains) | 12/15/18/21/24 words; BIP39 vs Electrum distinction; suggest derivation paths |

### Chain format specs (locked-in reference)

**Monero (XMR):**
- 69 bytes = 1-byte network (`0x12` mainnet / `0x35` testnet / `0x18` stagenet) + 32-byte spend pubkey + 32-byte view pubkey + 4-byte checksum
- Checksum = first 4 bytes of **Keccak-256** of preceding 65 bytes
- Base58 = Bitcoin alphabet but **block-encoded** (8-byte blocks → 11 chars each, last block carries remainder). NOT whole-payload. ~95 chars mainnet.
- Subaddresses start `8`, integrated (with payment ID) start `4`

**Cardano (ADA):**
- Bech32 HRPs: `addr1`, `stake1`, `addr_test1` (testnet), `ptr1` (pointer)
- Byron legacy = base58 starting `DdzFFz`
- Internal: header (type+network) + 28-byte payment credential + optional 28-byte stake credential

**Tezos (XTZ):**
- Base58Check, 36 chars. PKH = 20-byte Blake2b digest
- Prefix bytes: `tz1`=`06a19f` (Ed25519), `tz2`=`06a1a1` (secp256k1), `tz3`=`06a1a4` (P-256), `tz4`=`06a1a0` (BLS12-381)

**Polkadot (DOT) SS58:**
- `Base58( prefix | pubkey | checksum )`
- Prefix: `0`=Polkadot, `2`=Kusama, etc.
- Checksum = first N bytes of **Blake2b-512** with domain separator `"SS58PRE"` (0x53533538505245) prepended
- Checksum length: payload ≤32B → 2B; 33–37B → 3B; ≥38B → 4B

**TON:**
- 36-byte raw = tag(1) + workchain(1) + 32-byte hash
- Tag: `0x11` bounceable, `0x51` non-bounceable, `0x80` testnet bit ORed
- Append 2-byte **CRC16-XMODEM** → 34 bytes → Base64/Base64URL
- Mainnet: `EQ...`/`UQ...`. Testnet: `kQ...`/`0Q...`

**Algorand (ALGO):**
- 32-byte Ed25519 pubkey + 4-byte checksum (first 4 bytes of **SHA512/256** of pubkey) → Base32 RFC4648 unpadded → exactly **58 chars**

**Cosmos family:**
- All secp256k1, BIP44 path `m/44'/118'/0'/0/0`. Same 20-byte pubkey-hash, only HRP differs. 45 chars.
- HRPs: `cosmos`, `osmo`, `juno`, `akash`, `secret`, `persistence`, `kava`, `inj`, `evmos`, `stride`, `stars`, `regen`, `cre`, `sent`, `like`, `axelar`, `cro`, `terra`, `band`, `umee`, + valoper/valcons variants

**Stellar (XLM):**
- 33 bytes (version `0x30`=`G` + 32-byte Ed25519) + 2-byte **CRC16-XMODEM** → Base32 RFC4648 unpadded → **56 chars**
- Secret keys: version `0x90` → starts `S`
- Muxed accounts (SEP-23): `M`, 69 chars

**Tron (TRX):**
- `0x41` + 20-byte Keccak-256 pubkey hash + 4-byte double-SHA256 checksum → Base58Check
- 25 bytes → always starts `T`. 34 chars.

**Sui / Aptos:**
- Both: `0x` + 64 hex
- Sui address = **BLAKE2b** of pubkey (scheme-flagged)
- Aptos = **SHA3-256**
- Schemes: Ed25519, secp256k1, secp256r1
- Distinguish from ETH (40 hex) by length

**Near:**
- Implicit: 64 lowercase hex = 32-byte Ed25519 pubkey, no `0x`
- Named accounts: regex match `^[a-z0-9-]+\.near$` (low value, near-exclusively skipped)

**Solana:**
- 32-byte Ed25519 pubkey → Base58 (Bitcoin alphabet)
- **32–44 chars** (usually 43–44)
- No checksum (confidence caps at 50)

### Standards nuance

**bech32 vs bech32m (BIP-173 vs BIP-350):**
- Identical machinery. Only difference: trailing polymod constant — bech32=`0x01`, bech32m=`0x2bc830a3`
- v0 SegWit (`bc1q`) → bech32. v1+ / Taproot (`bc1p`) → bech32m. Implementation branches on witness version.
- For v0, limit data to 20 or 32 bytes per BIP-350 softened rule.

**BIP39 mnemonic validation:**
- ENT/CS/MS table: 128/4/12, 160/5/15, 192/6/18, 224/7/21, 256/8/24
- Checksum = first **ENT/32 bits** of SHA-256(entropy)
- Validate: re-split bits → indices → wordlist lookup → checksum recompute
- Wordlist: 2048 words (`english.txt`); other languages available (Spanish, Japanese, Korean, Chinese-s/t, French, Italian, Czech, Portuguese)
- **Electrum ≠ BIP39**: same wordlist, HMAC-based checksum + version byte, NOT BIP39-compatible. Detect version prefix → flag as Electrum.

**EIP-55 checksum (ETH address checksum):**
- lowercase hex addr (no `0x`) → Keccak-256 as ASCII → for each char `i`, if it's `a-f` AND hash nibble `i` ≥ 8 → uppercase. Digits unchanged. ~15 bits detection. Single-char corruption detectable.

---

## Confidence scoring

No industry standard exists. Adopted tiers:

| Score | Tier | When |
|-------|------|------|
| 100 | `valid_checksum` | Strict format match + checksum passes, no repairs |
| 85 | `valid_after_minor_repair` | Valid after whitespace/case/prefix normalization |
| 70 | `valid_after_encoding_repair` | Valid after hex↔base58↔base64 conversion |
| 60 | `valid_after_ocr_repair` | Valid after visual char swap (0↔O, 1↔l↔I) |
| 50 | `format_match_no_checksum` | Format matches, no checksum exists (e.g. SOL) |
| 40 | `checksum_failed_likely_typo` | Format matches, checksum FAILED (likely corruption) |
| 30 | `partial_match` | Redaction/partial key, structure-only match |
| 20 | `plausible_charset_length` | Only charset+length match shape |
| 10 | `high_entropy_only` | High entropy but no format match |

---

## Repair strategy

Escalating stages. Cap: max **50 candidate variants per input** across all stages.

| Stage | Primitive | Example | Cost |
|-------|-----------|---------|------|
| 1 (always) | Whitespace strip (incl. unicode zero-width) | `"bc 1q...\n"` → `"bc1q..."` | trivial |
| 1 | Prefix normalize (drop `0x`, `bc1`, `addr1`) | `0xdead...` → `dead...` | trivial |
| 1 | Case normalize (lower, upper, EIP-55 fix) | `0xABC...DEF` → EIP-55 corrected | trivial |
| 2 (if 1 fails) | OCR confusables (one char at a time) | `O` → `0`, `l` → `1`, `S` → `5` | low |
| 3 (if 2 fails) | Encoding round-trip (hex↔base58↔base64) | hex string → decode → re-encode base58 | low |
| 4 (if 3 fails) | Length repair (±2 chars, bounded) | insert/delete at each position | medium |
| 5 (give up) | Mark as redacted/partial | `bc1q...xyz` flagged partial, format-only match | n/a |

**Break on first valid:** once any candidate validates with checksum pass, pipeline stops repairing.

**BIP39 special case:** instead of char-level repairs, **Levenshtein distance ≤2** against the 2048-word BIP39 English wordlist. `"abondon"` → `"abandon"`. Max 3 word fixes per mnemonic. Lives in `mnemonic.py`, not generic layer.

**Repair metadata:** every repair tagged in `Candidate.repairs` (e.g. `["strip-ws", "case:eip55", "ocr:O→0"]`) and surfaces in `Match.repairs_applied`. Critical for trust.

---

## Output modes & CLI

**Auto-selected modes** (overridable):

- **Rich** (default for 1 input) — full breakdown with cross-chain alternates, wallet compatibility, repairs applied
- **Terse** (default for 2+ inputs) — one line each: `INPUT → CHAIN/FORMAT (confidence%) [checksum-status]`
- **JSON** (`--json` flag) — structured output for piping

**Example rich output:**
```
$ classify-key 0x7c13fff2d7e8b1f7b8e1d8a1f3c5b8a1f3c5b8a1
INPUT: 0x7c13fff2d7e8b1f7b8e1d8a1f3c5b8a1f3c5b8a1

✓ MATCH (100%): Ethereum address
    Chain:        ETH (and 20+ EVM L2s: Polygon, Base, Arbitrum, ...)
    Format:       keccak256 hash160 (20-byte)
    Key type:     address
    Checksum:     EIP-55 valid
    Network:      mainnet
    Wallets:      MetaMask, Trust, Ledger, Trezor, MEW, Rainbow, Coinbase Wallet
```

**Example terse output:**
```
$ classify-key --file keys.txt
0x7c13...b8a1                  → ETH/address (100%, checksum valid)
bc1qxy2kgdygjrsqtzq2n0yrf2493  → BTC/bech32-segwit (100%, checksum valid)
7c13fff2d7e8b1f7b8e1d3c5b8a1f  → SOL/address (50%, no checksum exists)
```

**CLI flags:**
- `--rich` / `--terse` / `--json` — override auto-mode
- `--mask` (default ON for private keys) — `5Kb8...3MaT` instead of full key
- `--no-mask` — show full keys (warns to stderr first)
- `--cross-chain` / `--no-cross-chain` (default ON)
- `--wallets` / `--no-wallets` (default ON)
- `--min-confidence N` — filter out matches below threshold
- `--chains btc,eth,sol` — whitelist validators
- `--explain` — include repair trace in output

**Batch input sources:**
- Positional: `classify-key abc def`
- stdin: `cat keys.txt | classify-key`
- File: `classify-key --file keys.txt`
- One input per line; `#` = comment

**Privacy / safety:**
- Default masking for private keys (never accidentally print WIF/seed)
- Warning to stderr on high-confidence private key match with `--no-mask`
- Zero network calls; pure local; no telemetry; no key material leaves process
- README warning: "Do not pipe unmasked output to logs, cloud storage, or LLM prompts"
- Test fixtures use ONLY documented public vectors; no real mainnet keys

---

## Testing

Three layers:

**Unit tests** — one file per validator, against public test vectors:
- BTC: BIP-173 bech32 reference + Bitcoin Core test vectors
- ETH: EIP-55 reference addresses
- SOL: Solana web3.js fixtures
- BIP39: Trezor's `python-mnemonic` test vectors
- Monero/Tezos/Polkadot/etc: official docs' example addresses
- Each `tests/fixtures/<chain>_vectors.json` documents its source URL

**Pipeline integration tests** — end-to-end cases:

| Input | Expected |
|-------|----------|
| Clean BTC address | 100% confidence, no repairs |
| BTC address with whitespace | 85%, repair noted |
| BTC address with 1 wrong char | 40% (checksum failed) + likely-fix suggestion |
| ETH address with `0`→`O` OCR swap | 60-100% depending on post-repair checksum |
| Truncated SOL address (30 chars) | 30% partial match |
| Random garbage | no match |
| 12-word BIP39 mnemonic | 100%, derivation paths suggested |
| BIP39 with typo'd word | repaired via Levenshtein, 70% |
| Electrum mnemonic | 100%, flagged "Electrum, not BIP39" |
| Cosmos address | 100% + 20+ cross-chain alternates |

**Property tests (fuzzing):**
- Generate random valid keys per chain using reference libraries
- Apply 1-3 random mutations (char swap, deletion, OCR substitution)
- Assert: classifier still identifies correct chain ≥90% of the time for single-char mutations

**Snapshot tests:**
- Confidence scores and output format pinned via `pytest-snapshot`
- `--snapshot-update` for intentional changes

**CI:**
- All tests offline
- Coverage: 90%+ on validators, 95%+ on pipeline/preprocessor
- Strict type-check (pyright strict mode)

---

## Implementation phases (for the writing-plans skill to break into tasks)

Rough ordering, each phase independently testable:

1. **Skeleton + pipeline + 3 validators** (BTC, EVM, SOL) — proves the architecture. End-to-end test passes for clean inputs.
2. **Repair layer** (all 4 stages) — drives confidence scores up on corrupted inputs.
3. **Cross-chain expansion** for BTC family + Cosmos — proves the differentiating feature.
4. **Long-tail validators** (Monero, Cardano, Tezos, Polkadot, TON, Stellar, Tron, Algorand, Kaspa, Sui/Aptos, Near, Ripple).
5. **Mnemonic validator** (BIP39 + Electrum + Levenshtein repair).
6. **CLI modes** (rich/terse/json, masking, filters).
7. **Property tests + fuzzing harness**.

---

## Open questions for Jordan

1. **Test fixture sourcing:** I plan to use BIP-173 bech32 reference vectors, EIP-55 examples, Trezor's BIP-39 test vectors, and chain docs' published example addresses. None of these are "real" funded mainnet keys. Good?
2. **Wallet compatibility lists:** I'll seed these from each chain's official docs (e.g. `solana.com` lists Phantom/Solflare/Backpack). Multi-source — not exhaustive but accurate. Good?
3. **BIP39 wordlist languages:** English-only at first (it's the dominant case). Add Japanese/Spanish/etc. wordlists later if needed. Good?
4. **Package name:** `ckc` (crypto-key-classifier) for the Python module, `classify-key` for the CLI command. Good?

---

## References

- [BIP-173 Bech32](https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki)
- [BIP-350 Bech32m](https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki)
- [BIP-39 Mnemonic code](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki)
- [EIP-55 Mixed-case checksum](https://eips.ethereum.org/EIPS/eip-55)
- [CIP-5 Cardano common prefixes](https://cips.cardano.org/cip/CIP-5)
- [CIP-19 Cardano addresses](https://cips.cardano.org/cip/CIP-19)
- [Monero standard address docs](https://docs.getmonero.org/public-address/standard-address/)
- [Tezos account encoding](https://octez.tezos.com/docs/active/accounts.html)
- [SS58 Polkadot format](https://aandds.com/blog/polkadot.html)
- [TON address formats](https://docs.ton.org/foundations/addresses/formats)
- [ARC-1 Algorand address](https://github.com/algorandfoundation/ARCs/blob/main/ARCs/arc-0001.md)
- [SEP-23 Stellar muxed accounts](https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0023.md)
- [TruffleHog](https://github.com/trufflesecurity/trufflehog), [Gitleaks](https://gitleaks.org/), [detect-secrets](https://github.com/Yelp/detect-secrets) — surveyed, none do fuzzy recovery
