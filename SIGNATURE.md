# Signature

This repo follows the [Jordan Newell code-signature pattern](https://jordannewell.com/signature/). Three layers.

## Layer 1 — Style tells

| Rule | Example |
|---|---|
| Headline-first module docstring | `"""Classify any plausible crypto-key string with aggressive recovery."""` |
| Why-only comments | `# Mask private keys by default — terminal scrollback is a real exfil vector.` |
| Causality test naming | `test_argparse_help_no_bare_percent()`, `test_cosmos_hrp_swap_20_alternates()` |
| Headline function first | The public function in any file appears first; helpers below |

## Layer 2 — `__signature__` constant

```python
>>> import ckc
>>> ckc.__signature__
'jn/crypto-key-classifier@0.6.0'
```

Verified at runtime. Format: `jn/<repo-slug>@<version>`. Same format across every Jordan Newell repo.

## Layer 3 — PGP-signed commits and tags

All commits and tags signed with Jordan's signing key. Fingerprint:

```
67567DC5E7C5353F85F2AF0DAC05D3F3E0EFA32A
```

Key ID: `AC05D3F3E0EFA32A`. Type: Ed25519, expiry 2 years.

Retrieve the key via Web Key Directory:

```bash
gpg --auto-key-locate clear,dkd,nodefault --locate-key jordan@jordannewell.com
```

Or from a keyserver:

```bash
gpg --keyserver hkps://keys.openpgp.org      --recv-keys AC05D3F3E0EFA32A
gpg --keyserver hkps://keyserver.ubuntu.com  --recv-keys AC05D3F3E0EFA32A
```

Verify a commit:

```bash
git verify-commit HEAD
```

Verify a tag:

```bash
git verify-tag v0.5.0
```

## Verification cheat sheet

```bash
# Layer 2 — runtime signature
pip install -e .
python -c "import ckc; print(ckc.__signature__)"

# Layer 3 — git signature
git verify-commit HEAD
git verify-tag v0.5.0
```
