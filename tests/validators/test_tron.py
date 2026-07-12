import pytest

from ckc.models import Candidate
from ckc.validators.base import base58check_encode
from ckc.validators.tron import TronValidator


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module")
def tron_addr() -> str:
    """Generate a valid Tron address via base58check_encode(0x41 + 20-byte hash)."""
    return base58check_encode(b"\x41" + bytes(range(20)))


def test_tron_address_valid(tron_addr):
    v = TronValidator()
    m = v.validate(_cand(tron_addr))
    assert m is not None
    assert m.chain == "TRX"
    assert m.format == "base58check"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_tron_always_starts_with_T(tron_addr):
    # All valid Tron mainnet addresses start with 'T' because 0x41 prefix
    # produces a base58 string starting with T
    assert tron_addr.startswith("T")


def test_invalid_rejected():
    v = TronValidator()
    assert v.validate(_cand("not a tron address")) is None
    long_eth = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
    assert v.validate(_cand(long_eth)) is None


def test_shape_match(tron_addr):
    v = TronValidator()
    assert v.shape_match(_cand(tron_addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(tron_addr):
    v = TronValidator()
    m = v.validate(_cand(tron_addr))
    assert m is not None
    assert m.cross_chain_alternates == []
