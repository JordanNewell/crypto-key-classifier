"""Property tests for mnemonic validator.

Generate random valid 12-word BIP-39 mnemonics by sampling entropy and
computing the checksum. Then mutate (whitespace pollution, uppercase)
and verify the pipeline still identifies the result as BIP39.
"""

from __future__ import annotations

import hashlib
import os
from importlib import resources

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ckc.pipeline import classify


def _load_wordlist() -> list[str]:
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        return [line.strip() for line in f if line.strip()]


WORDS = _load_wordlist()


def _generate_valid_12_word() -> str:
    """Generate a valid 12-word BIP-39 mnemonic from random entropy."""
    entropy = os.urandom(16)  # 128 bits = 12-word mnemonic
    checksum = hashlib.sha256(entropy).digest()
    # ENT=128, CS=4 bits
    bits = "".join(format(b, "08b") for b in entropy)
    bits += format(checksum[0] >> 4, "04b")  # first 4 bits of checksum
    # Split into 11-bit groups, each -> word index
    indices = [int(bits[i:i + 11], 2) for i in range(0, 132, 11)]
    return " ".join(WORDS[i] for i in indices)


def _top_chain(corrupted: str) -> str | None:
    results = classify(corrupted)
    return results[0].chain if results else None


@given(st.builds(_generate_valid_12_word))
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_valid_mnemonic_classified_as_bip39(mnemonic):
    """A valid 12-word BIP-39 mnemonic must classify as BIP39."""
    chain = _top_chain(mnemonic)
    assert chain == "BIP39"


@given(st.builds(_generate_valid_12_word))
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_mnemonic_with_whitespace_recovered(mnemonic):
    """Mnemonic with whitespace pollution should still be recovered."""
    corrupted = "  " + mnemonic + "\n"
    chain = _top_chain(corrupted)
    assert chain == "BIP39"


@given(st.builds(_generate_valid_12_word))
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_mnemonic_uppercase_recovered(mnemonic):
    """Mnemonic in uppercase should be lowercased and recovered."""
    corrupted = mnemonic.upper()
    chain = _top_chain(corrupted)
    assert chain == "BIP39"
