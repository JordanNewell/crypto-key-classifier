# Contributing

Thanks for considering a contribution. This tool handles sensitive input
(crypto private keys, seed phrases) so the bar for correctness and test
coverage is higher than a typical CLI.

## Setup

```bash
git clone https://github.com/JordanNewell/crypto-key-classifier.git
cd crypto-key-classifier
pip install -e ".[dev]"
pytest                   # 239 tests, should be green
ruff check .
pyright                  # strict mode
```

Requires Python ≥ 3.10.

## Adding a validator (the most common contribution)

Validators auto-discover via `src/ckc/validators/__init__.py`. To add a
new chain:

1. Create `src/ckc/validators/your_chain.py` with a `Validator`
   subclass exposing `chain`, `formats`, `shape_match`, and `validate`.
2. Use an existing validator (e.g., `src/ckc/validators/cosmos.py`) as
   the shape template.
3. Add public test vectors to `tests/fixtures/your_chain/`. **Mainnet
   keys with real balances will be rejected.** Generate throwaway keys
   or use published test vectors.
4. Add unit tests in `tests/validators/test_your_chain.py`.
5. Add a property test in `tests/fuzz/` covering whitespace/case
   recovery and at least one checksum failure mode.
6. Update `README.md` validator table.

The validator joins the pipeline on next run — no registration step.

## Code style

- `ruff check .` clean (rules: E, F, I, B, UP; line-length 100)
- `pyright` strict mode clean (advisory on CI, **strict on dev box**)
- Module docstring follows the
  [signature pattern](https://jordannewell.com/signature/) —
  headline-first, one-line "what + why"
- Comments explain *why*, not *what* — see `SIGNATURE.md`

## Commits

- All commits must be signed (Ed25519 key in `SIGNATURE.md`).
  Configure `git config commit.gpgsign true` locally.
- Subject line ≤ 72 chars, imperative mood (`Add X`, `Fix Y`).
- Reference the issue number in the body if applicable.
- **No `Co-Authored-By: Claude` or other AI-attribution trailers.**
  Tools don't get attribution.

## Tests

Property tests live under `tests/fuzz/` and use
[Hypothesis](https://hypothesis.readthedocs.io/). When fixing a bug,
add a regression test that fails before your fix and passes after.

End-to-end tests under `tests/test_e2e.py` exercise the full pipeline —
run them with `pytest tests/test_e2e.py -v` to see the CLI output
format.

## Pull requests

Open a PR against `main`. CI must pass (Ruff + Pytest across Python
3.10/3.11/3.12). Pyright is advisory on CI but should be clean in your
branch — strict typing is the project's quality bar.

Branch protection is enabled on `main`; direct pushes are blocked.

## Security-relevant bugs

Do **not** open a public PR or issue for security vulnerabilities,
masking bypasses, or any bug that could leak key material. See
[`SECURITY.md`](SECURITY.md) for the private reporting path.
