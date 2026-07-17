# crypto-key-classifier (`classify-key` / `ckc`)

Classify any plausible crypto-key string — BTC / ETH / SOL / Cosmos family + a dozen more chains, plus BIP-39 and Electrum mnemonics — with aggressive recovery from formatting noise, bad checksums, wrong encodings, and OCR corruption. Recommends compatible wallets and enumerates cross-chain re-encodings for shared-key families (Cosmos IBC, EVM L2s, BTC forks, Polkadot SS58).

**Status:** v0.4.0-hardened, shipped. 229 tests, 17 validators covering ~50 chains, hypothesis fuzz suite.

## Why

If you've ever stared at a string like `0x7c13fff2d7e8...` or `bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh` and wondered *"is this an address or a private key? which chain? is the checksum valid?"* — this tool answers that, fast, locally, and without leaking the key to a lookup service.

Built for the recovery / forensics / support-ticket triage case: someone hands you a string and you need to (a) figure out what it is, (b) tell them what wallets will accept it, and (c) cross-check it against related chains they might also own.

## Install

```bash
pip install -e .

classify-key --help
```

Requires Python ≥ 3.10. Dependencies: `base58`, `pycryptodome`. Dev extras (`pytest`, `hypothesis`, `ruff`, `pyright`) via `pip install -e ".[dev]"`.

## Usage

```bash
# Classify one key — rich multi-line output (default for single input)
classify-key 0x7c13fff2d7e8b1f7b8e1d8a1f3c5b8a1f3c5b8a1

# Batch — one-line-per-key (default for 2+ inputs)
classify-key addr1.txt addr2.txt
classify-key --file keys.txt
cat keys.txt | classify-key

# JSON for scripting — pipe to jq
classify-key --json addr.txt | jq '.[] | .best_guess'

# Narrow to specific chains
classify-key --chains btc,eth,sol <input>

# Filter low-confidence matches
classify-key --min-confidence 80 <input>

# Show the repair trace (what mutations recovered a corrupted input)
classify-key --explain <input>

# Print full private keys (DANGEROUS — read the Safety section)
classify-key --no-mask <input>
```

## Validator coverage (17 validators, ~50 chains)

| Validator | Chains | Notable |
|---|---|---|
| `btc` | BTC, LTC, DOGE | WIF private keys + legacy/segwit/bech32 addresses via prefix byte |
| `evm` | ETH + Polygon, Arbitrum, Base, Optimism, BSC, Avalanche, Gnosis, Linea, Scroll, Zora | EIP-55 checksum, same key → 11 cross-chain addresses |
| `sol` | Solana | base58 ed25519 pubkey (32 bytes) or secret key (64 bytes) |
| `cosmos` | ATOM, OSMO, JUNO, AKT, INJ, EVMOS, STRD, REGEN, XPRT, SCRT, KAVA, CRO, LUNA, BAND, UMEE, STARS, DVPN, LIKE, AXL, CRE | **Headline feature:** one decode → 20 cross-chain HRP re-encodings |
| `cardano` | ADA | bech32 `addr1` / `stake1` / `addr_test1` |
| `polkadot` | DOT, KSM | SS58 with Blake2b-512 + SS58PRE domain separator |
| `ripple` | XRP | custom base58 alphabet, `0x00` prefix |
| `stellar` | XLM | base32 + CRC16-XMODEM (G account / S secret) |
| `tron` | TRX | base58check, `0x41` prefix |
| `algorand` | ALGO | base32 + SHA512/256 checksum |
| `tezos` | XTZ | base58check, 4 prefix types (Ed25519 / secp256k1 / P-256 / BLS12-381) |
| `ton` | TON | base64 + CRC16-XMODEM, bounceable / non-bounceable |
| `monero` | XMR | block-encoded base58 + Keccak-256, 95-char mainnet |
| `sui_aptos` | Sui, Aptos | `0x` + 64 hex (structurally ambiguous — flagged) |
| `near` | NEAR | implicit 64-hex ed25519 + named accounts |
| `kaspa` | KAS | bech32 `kaspa` / `kaspatest` HRPs |
| `mnemonic` | BIP-39 (12/15/18/21/24 words), Electrum (12/13 words) | Levenshtein word repair for OCR / typos |

## The Cosmos HRP swap (why this tool exists)

The same Ed25519 private key underlies every Cosmos SDK chain. Decode the bech32 once, re-encode with a different human-readable prefix (HRP), and you have a valid address on every chain in the family:

```
$ classify-key cosmos1... --json | jq '.[0].cross_chain_alternates | length'
20
```

Twenty chains, one key. If you've ever recovered an ATOM wallet and wondered *"do I also own the OSMO/JUNO/AKT at the matching address?"* — yes, you do. This tool enumerates them.

The same pattern applies to EVM (11 L2s from one address) and BTC forks (LTC/DOGE from one WIF).

## Recovery pipeline

Each input runs through three stages:

1. **Preprocess** — strips whitespace, normalizes confusables (`O`→`0`, `l`→`1`), handles case folds, removes invisible characters, copes with copy-paste artifacts.
2. **Validate** — for each of the 17 validators, shape-match (length/charset) → strict validate (checksum, prefix, structure). Short-circuits on first `checksum_status: valid` match.
3. **Repair** (optional) — if nothing matches clean, generate aggressive candidates: OCR substitutions, encoding variants (hex↔base58↔base64), Levenshtein word fixes for mnemonics. Cap to bound runtime.

`classify-key --explain <input>` shows the repair trace so you can see *what was wrong* and *what fix recovered it*.

## Safety

- **Default masking** for private keys — WIF / seed phrases / secret keys print as `bc1q…wlh (8 chars masked)` unless you pass `--no-mask`. Never accidentally leak a key to your terminal scrollback.
- **Zero network calls** — pure local, no telemetry, no key material leaves the process.
- **Public test vectors only** in `tests/fixtures/` — no real mainnet keys in the repo.
- `--no-mask` prints a warning to stderr before any output. Do not pipe `--no-mask` output to logs, cloud storage, or LLM prompts.

## Development

```bash
pip install -e ".[dev]"

# Run the full suite (229 tests)
pytest

# Property tests via hypothesis
pytest tests/fuzz

# Lint + typecheck
ruff check .
pyright
```

Validators auto-discover via `src/ckc/validators/__init__.py` — drop a new `foo.py` with a `Validator` subclass exposing `chain`, `formats`, `shape_match`, and `validate`, and it joins the pipeline on next run.

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for releases `v0.1.0-mvp` → `v0.4.0-hardened`.

## License

MIT — see [`LICENSE`](LICENSE).
