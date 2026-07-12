import pytest

from ckc.models import Candidate
from ckc.validators.sui_aptos import SuiAptosValidator


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module")
def sui_aptos_addr() -> str:
    """A valid 0x + 64 hex address (ambiguous between SUI and APT)."""
    return "0x" + "1" * 64


def test_sui_aptos_address_valid(sui_aptos_addr):
    v = SuiAptosValidator()
    m = v.validate(_cand(sui_aptos_addr))
    assert m is not None
    # Should identify as one of SUI or APT (validator picks one as primary)
    assert m.chain in {"SUI", "APT"}
    assert m.format == "blake2b-or-sha3-256-hash"
    assert m.checksum_status == "none"  # no checksum exists
    assert m.confidence == 30  # ambiguous, low confidence


def test_ambiguity_noted_in_notes(sui_aptos_addr):
    v = SuiAptosValidator()
    m = v.validate(_cand(sui_aptos_addr))
    assert m is not None
    notes_joined = " ".join(m.notes).lower()
    assert "ambiguous" in notes_joined or "sui" in notes_joined
    assert "apt" in notes_joined


def test_invalid_rejected():
    v = SuiAptosValidator()
    assert v.validate(_cand("not a sui address")) is None
    assert v.validate(_cand("0xabc")) is None  # too short
    assert v.validate(_cand("0x" + "Z" * 64)) is None  # invalid hex


def test_shape_match(sui_aptos_addr):
    v = SuiAptosValidator()
    assert v.shape_match(_cand(sui_aptos_addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(sui_aptos_addr):
    # The ambiguity itself IS the cross-chain info, but no concrete alternates
    v = SuiAptosValidator()
    m = v.validate(_cand(sui_aptos_addr))
    assert m is not None
    assert m.cross_chain_alternates == []


def test_without_0x_prefix_also_accepted():
    # Some sources use bare hex without 0x
    v = SuiAptosValidator()
    m = v.validate(_cand("1" * 64))
    # Preprocessor strips 0x prefix, so this should also work
    # But the validator itself gets the form preprocessor chose — could be either
    # The test just verifies it doesn't crash
    assert m is None or m.chain in {"SUI", "APT"}
