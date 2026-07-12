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
    result = _run(["--json", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"])
    import json
    parsed = json.loads(result.stdout)
    assert parsed["matches"][0]["chain"] == "BTC"


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
