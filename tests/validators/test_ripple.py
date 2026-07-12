import pytest

from ckc.models import Candidate
from ckc.validators.ripple import RippleValidator, ripple_base58check_encode


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module")
def ripple_addr() -> str:
    """Generate a valid Ripple address using ripple_base58check_encode."""
    return ripple_base58check_encode(b"\x00" + bytes(range(20)))


def test_ripple_address_valid(ripple_addr):
    v = RippleValidator()
    m = v.validate(_cand(ripple_addr))
    assert m is not None
    assert m.chain == "XRP"
    assert m.format == "base58check"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_ripple_always_starts_with_r(ripple_addr):
    # 0x00 prefix encodes to 'r' in Ripple's custom alphabet
    assert ripple_addr.startswith("r")


def test_invalid_rejected():
    v = RippleValidator()
    assert v.validate(_cand("not a ripple address")) is None
    # A Bitcoin address (different alphabet) should NOT validate as Ripple
    assert v.validate(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")) is None


def test_shape_match(ripple_addr):
    v = RippleValidator()
    assert v.shape_match(_cand(ripple_addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(ripple_addr):
    v = RippleValidator()
    m = v.validate(_cand(ripple_addr))
    assert m is not None
    assert m.cross_chain_alternates == []
