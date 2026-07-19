# Changelog

All notable changes to `crypto-key-classifier` are documented here. Tags follow `vMAJOR.MINOR.PATCH-label` semantics where the label signals a ship milestone rather than strict semver breakage (pre-1.0).

## [Unreleased]

## [v0.6.1-pypi] — 2026-07-19

### Added
- First PyPI release. `pip install crypto-key-classifier` now works for
  anyone, no source clone required.
- GitHub Actions release workflow (`.github/workflows/release.yml`)
  publishes to PyPI automatically on signed `v*` tag push. Uses OIDC
  trusted publishing — no API tokens stored in repo secrets.
- `classifiers` and `[project.urls]` populated in `pyproject.toml` so
  PyPI's project page shows topics, license, Python versions, and links
  to repo / changelog / issues.
- CI workflow (`.github/workflows/ci.yml`) committed. Matrix across
  Python 3.10 / 3.11 / 3.12 on every push and PR; Ruff + Pytest gating,
  Pyright advisory.

### Changed
- README install section: PyPI is now the primary path; source clone
  moved under "Development install".
- Version bump `0.6.0` → `0.6.1`.

## [v0.6.0-stranger-fixes] — 2026-07-19

### Fixed
- `--chains` now accepts case-insensitive chain codes. README documented
  `--chains btc,eth,sol` (lowercase), but the pipeline filter required
  uppercase (`BTC,ETH,SOL`), so copy-pasting from the README produced
  "No matches found" on valid keys. Codes are now upper-cased before the
  whitelist is built.
- `--json` now emits a single JSON array wrapping all results. Previously
  each input produced a separate JSON object (concatenated), so the
  documented `classify-key --json addr.txt | jq '.[] | .best_guess'`
  pipeline failed with `jq` exit 5 ("Cannot index string with string").
  Single-input output is now a one-element array for consistency.
- `--file` with a missing or unreadable path now prints a one-line error
  to stderr and exits 2. Previously raised an uncaught `FileNotFoundError`
  traceback.
- Long inputs (e.g. paste-corrupted keys with thousands of trailing
  characters) no longer dump the entire blob into the `INPUT:` echo line.
  Inputs longer than 80 chars are truncated to `prefix…suffix` after
  masking, so the recognizable head and tail stay visible.
- `--help` description: "aggressive recovering" → "aggressive recovery".

### Added
- `render_json_array(items, mask_private_keys=...)` in `ckc.reporter` for
  batch JSON emission.
- `truncate_for_display(s, max_len=80)` helper, used by rich and terse
  renderers.
- 10 regression tests covering the five stranger-test bugs.

### Stranger test context
Discovered via a fresh-clone stranger install + adversarial CLI exercise
on 2026-07-19. Two of the five bugs (`--chains` case sensitivity, `--json`
array shape) broke the README's own examples on first use. Full report in
the session log; test scenarios reproduced in `tests/test_cli.py` and
`tests/test_reporter.py`.

## [v0.5.0-signature] — 2026-07-17

### Added
- `__signature__` runtime constant in `ckc.__init__` — exports the string `jn/crypto-key-classifier@0.5.0` so any consumer can verify authorship at runtime: `python -c "import ckc; print(ckc.__signature__)"`.
- `SIGNATURE.md` at repo root documenting the three-layer code-signature pattern (style tells, `__signature__`, PGP-signed commits).
- Headline-first imperative docstrings across `pipeline.py` and `cli.py` (Layer 1 style tell).

### Changed
- Version bump `0.4.0` → `0.5.0`. The signature work is structural, not behavior-changing.

### Fixed
- `--help` no longer crashes on `argparse` bare-`%` interpolation (escaped as `%%` in help string). Two regression tests added to prevent recurrence. ([`b79e998`](commit/b79e998), [`f70ef12`](commit/f70ef12))

## [v0.4.0-hardened] — 2026-07-12

### Added
- Hypothesis property/fuzz test suite under `tests/fuzz/`.
- Per-validator property tests: whitespace recovery + sanity for MVP chains (BTC/EVM/SOL/Cosmos), long-tail validators (TRX/XLM/DOT/XMR), BIP-39 mnemonic generation + whitespace/case recovery.
- Aggregate fuzz recovery-rate test asserts a minimum acceptable recovery floor across all chains.

### Fixed
- Preprocessor now preserves internal whitespace for mnemonic inputs (was over-aggressively collapsing spaces between words, breaking Levenshtein repair).

## [v0.3.0-mnemonic] — 2026-07-12

### Added
- `mnemonic` validator — BIP-39 (12/15/18/21/24 words) and Electrum (12/13 words) with wordlist integrity check.
- BIP-39 English wordlist bundled (`src/ckc/data/`).
- Levenshtein distance helper (`src/ckc/repairs.py`) used to suggest corrections for typo'd mnemonic words.
- End-to-end mnemonic tests; reporter masking correctly hides seed phrases by default.

## [v0.2.0-long-tail] — 2026-07-12

### Added
- 12 additional chain validators: Tron, Ripple, Algorand, Tezos, Stellar, Polkadot (DOT/KSM), TON, Monero, Cardano, Sui/Aptos, Near, Kaspa.
- Long-tail crypto helpers: CRC16-XMODEM, Blake2b-512, SHA512/256, Monero block-encoded base58.
- Extended wallet compatibility database to cover new chains.
- Pipeline now exposes per-validator `chain_codes` so the `--chains` whitelist works for family validators (BTC/EVM/Cosmos/DOT).

## [v0.1.0-mvp] — 2026-07-12

### Added
- Project scaffold (`pyproject.toml`, `src/ckc/` layout, base58/pycryptodome deps).
- Stage 1 preprocessor: whitespace normalization, prefix stripping (`0x`), case variants.
- Stage 2-4 repair primitives: OCR substitution, encoding variants (hex/base58/base64), length fixups.
- Validator protocol + shared crypto helpers (Keccak-256, base58check, bech32 reference impl).
- Four MVP validators:
  - **BTC family** — BTC/LTC/DOGE/BCH via prefix byte, WIF private keys, legacy/segwit/bech32 addresses.
  - **EVM** — ETH + 10 L2s (Polygon, Arbitrum, Base, Optimism, BSC, Avalanche, Gnosis, Linea, Scroll, Zora) with EIP-55 checksum and cross-chain address enumeration.
  - **Solana** — ed25519 base58, 32-byte pubkey / 64-byte secret key.
  - **Cosmos** — 20-chain IBC family with the headline HRP-swap cross-chain re-encoding.
- Pipeline orchestrator with ranked match output + short-circuit on valid checksum.
- Reporter: rich / terse / JSON output modes, default private-key masking.
- CLI entry point (`classify-key`) supporting stdin, `--file`, batch, and all output modes.
- Wallet compatibility database seeded for the four MVP families.
- End-to-end smoke test suite.

[Unreleased]: https://github.com/JordanNewell/crypto-key-classifier/compare/v0.6.1-pypi...HEAD
[v0.6.1-pypi]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.6.1-pypi
[v0.6.0-stranger-fixes]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.6.0-stranger-fixes
[v0.5.0-signature]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.5.0-signature
[v0.4.0-hardened]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.4.0-hardened
[v0.3.0-mnemonic]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.3.0-mnemonic
[v0.2.0-long-tail]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.2.0-long-tail
[v0.1.0-mvp]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.1.0-mvp
