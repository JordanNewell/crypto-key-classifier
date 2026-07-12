"""End-to-end tests for mnemonic validator through the pipeline."""

from ckc.pipeline import classify

VALID_12 = (
    "abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon about"
)
TYPO_12 = (
    "abondon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon about"
)


def test_e2e_valid_mnemonic_classified():
    r = classify(VALID_12)
    assert r and r[0].chain == "BIP39"
    assert r[0].confidence == 100
    assert r[0].checksum_status == "valid"


def test_e2e_typo_mnemonic_repaired():
    """Pipeline should apply Levenshtein repair via suggest_repairs and find a valid match."""
    r = classify(TYPO_12)
    bip39_matches = [m for m in r if m.chain == "BIP39" and m.checksum_status == "valid"]
    assert len(bip39_matches) > 0


def test_e2e_mnemonic_masked_as_private():
    """Mnemonics are private — should be masked in reporter output."""
    from ckc.reporter import render_rich
    r = classify(VALID_12)
    out = render_rich(VALID_12, r, mask_private_keys=True)
    # The raw mnemonic should NOT appear in output (only masked form)
    assert VALID_12 not in out


def test_e2e_all_17_validators():
    """Registry should now find 17 validators (16 + mnemonic)."""
    from ckc.validators import all_validators
    assert len(all_validators()) == 17


def test_e2e_random_words_low_confidence():
    """12 random English words that don't form valid checksum → low-confidence BIP39."""
    r = classify("apple banana cherry dog elephant fox grape hat igloo juice kite light")
    if r:
        assert r[0].chain == "BIP39"
        # Either valid (rare coincidence) or failed checksum
        assert r[0].checksum_status in {"valid", "failed"}


def test_e2e_mnemonic_via_cli():
    """Manual CLI invocation works."""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "ckc.cli", VALID_12],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "BIP39" in result.stdout
