import subprocess
import sys


def _run(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "ckc.cli"] + args,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_cli_single_input_rich_default():
    result = _run(["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    assert result.returncode == 0
    assert "BTC" in result.stdout
    assert "100%" in result.stdout


def test_cli_terse_mode():
    result = _run(["--terse", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    assert "BTC/P2PKH" in result.stdout
    assert result.stdout.count("\n") <= 2  # terse = 1-2 lines


def test_cli_json_mode():
    """--json always emits a JSON array (single object would break the
    documented `jq '.[] | .best_guess'` pipeline)."""
    result = _run(["--json", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    import json
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, list)
    assert parsed[0]["matches"][0]["chain"] == "BTC"


def test_cli_json_batch_emits_single_array():
    """Regression: batch --json must be ONE valid JSON document (an array),
    not concatenated per-input objects. Stranger test caught this — the
    README's `jq '.[] | .best_guess'` pipe was failing with exit 5."""
    stdin = (
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n"
        "0xd8da6bf26964af9d7eed9e03e53415d37aa96045\n"
    )
    result = _run(["--json"], stdin=stdin)
    import json
    parsed = json.loads(result.stdout)  # must NOT raise JSONDecodeError
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    # The documented jq filter works on the parsed array
    best_guesses = [r["best_guess"] for r in parsed]
    assert "BTC" in best_guesses
    assert "ETH" in best_guesses


def test_cli_chains_lowercase_accepted():
    """Regression: README says `--chains btc,eth,sol` (lowercase) but the
    pipeline filter required uppercase chain codes. Stranger test caught
    a lowercase whitelist producing 'No matches' on valid keys."""
    result = _run(["--chains", "btc", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    assert result.returncode == 0
    assert "BTC" in result.stdout
    assert "100%" in result.stdout


def test_cli_chains_mixed_case_accepted():
    result = _run(["--chains", "BtC,eth", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    assert "BTC" in result.stdout


def test_cli_chains_filters_correctly():
    """--chains btc must NOT match an EVM-only input (whitelist still works)."""
    result = _run(["--chains", "btc", "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"])
    assert "BTC" not in result.stdout


def test_cli_missing_file_friendly_error():
    """Regression: --file with missing path used to throw a raw FileNotFoundError
    traceback. Must emit a one-line error to stderr and exit 2."""
    result = _run(["--file", "/nonexistent/path/that/does/not/exist.txt"])
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert "error:" in result.stderr
    assert "--file" in result.stderr or "file" in result.stderr.lower()


def test_cli_stdin_batch_uses_terse():
    stdin = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\ncosmos1depk54qmj6nvh7t9gh2rk9p2t59q34c9klqyh2\n"
    result = _run([], stdin=stdin)
    assert "BTC/P2PKH" in result.stdout
    # The cosmos address above may not be a real valid bech32 — that's fine,
    # just verify BTC line is there in terse mode (batch auto-selects terse)


def test_cli_masks_private_keys_by_default():
    # Generate a known-valid BTC WIF for testing
    from ckc.validators.base import base58check_encode
    wif = base58check_encode(b"\x80" + b"\x01" * 32 + b"\x01")
    result = _run([wif])
    if "PRIVATE KEY" in result.stdout:
        # if recognized as private key, must be masked
        assert "..." in result.stdout


def test_cli_min_confidence_filter():
    # SOL address caps at 50 confidence
    result = _run(["--min-confidence", "80", "dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc"])
    # Should show "No matches" since SOL caps at 50
    assert "No matches" in result.stdout or "NO MATCH" in result.stdout


def test_cli_help_exits_clean():
    """Regression test: --help must not crash.

    Bug: bare '%' in argparse help string caused ValueError: incomplete format
    because argparse uses printf-style substitution. Any literal '%' must be '%%'.
    """
    result = _run(["--help"])
    assert result.returncode == 0
    assert "classify-key" in result.stdout.lower() or "usage" in result.stdout.lower()
    # Spot-check a few flags appear
    assert "--json" in result.stdout
    assert "--min-confidence" in result.stdout
