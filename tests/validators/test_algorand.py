import pytest

from ckc.models import Candidate
from ckc.validators.algorand import AlgorandValidator, algorand_encode_address


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module")
def algo_addr() -> str:
    """Generate a valid Algorand address from a known 32-byte pubkey."""
    pubkey = bytes(range(32))
    return algorand_encode_address(pubkey)


def test_algo_address_valid(algo_addr):
    v = AlgorandValidator()
    m = v.validate(_cand(algo_addr))
    assert m is not None
    assert m.chain == "ALGO"
    assert m.format == "ed25519-pubkey-base32"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_algo_address_length(algo_addr):
    # Algorand addresses are always exactly 58 chars (32 bytes -> 52 base32 chars
    # with padding, but unpadded -> 52 chars + 4 char checksum encoded as base32
    # -> actually let me recompute: 36 bytes -> 58 base32 chars unpadded)
    assert len(algo_addr) == 58


def test_invalid_rejected():
    v = AlgorandValidator()
    assert v.validate(_cand("not an algorand address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_shape_match(algo_addr):
    v = AlgorandValidator()
    assert v.shape_match(_cand(algo_addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(algo_addr):
    v = AlgorandValidator()
    m = v.validate(_cand(algo_addr))
    assert m is not None
    assert m.cross_chain_alternates == []
