# crypto-key-classifier (ckc)

Classifies any plausible crypto-key string (BTC/ETH/SOL + 15+ chains, BIP39/Electrum mnemonics) with aggressive recovery from formatting noise, bad checksums, wrong encodings, and OCR corruption. Recommends compatible wallets and enumerates cross-chain re-encodings for shared-key families (Cosmos IBC, BTC forks, Polkadot networks).

**Status:** Design phase (spec under `docs/superpowers/specs/`). Not yet implemented.

## Quick start (once implemented)

```bash
pip install -e .

# Classify one key (rich output)
classify-key 0x7c13fff2d7e8b1f7b8e1d8a1f3c5b8a1f3c5b8a1

# Batch (terse one-line-per-key output)
cat keys.txt | classify-key

# JSON output for scripting
classify-key --json addr.txt | jq '.[] | .best_guess'
```

## Safety

- **Default masking** for private keys — never accidentally print WIF/seed to terminal
- **Zero network calls** — pure local, no telemetry, no key material leaves the process
- **Public test vectors only** in fixtures — no real mainnet keys in repo
- Do NOT pipe `--no-mask` output to logs, cloud storage, or LLM prompts

## Design

See [`docs/superpowers/specs/2026-07-12-crypto-key-classifier-design.md`](docs/superpowers/specs/2026-07-12-crypto-key-classifier-design.md) for the full design spec.
