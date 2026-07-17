# Changelog

All notable changes to `crypto-key-classifier` are documented here. Tags follow `vMAJOR.MINOR.PATCH-label` semantics where the label signals a ship milestone rather than strict semver breakage (pre-1.0).

## [Unreleased]

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

[Unreleased]: https://github.com/JordanNewell/crypto-key-classifier/compare/v0.4.0-hardened...HEAD
[v0.4.0-hardened]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.4.0-hardened
[v0.3.0-mnemonic]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.3.0-mnemonic
[v0.2.0-long-tail]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.2.0-long-tail
[v0.1.0-mvp]: https://github.com/JordanNewell/crypto-key-classifier/releases/tag/v0.1.0-mvp
