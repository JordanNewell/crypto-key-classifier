import pytest

from ckc.models import Candidate
from ckc.validators.ton import TONValidator, ton_encode


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module", params=[
    (0x11, "EQ", "mainnet-bounceable"),
    (0x51, "UQ", "mainnet-non-bounceable"),
])
def ton_addr(request) -> str:
    """Generate a valid TON address."""
    tag, _, _ = request.param
    # tag(1) + workchain(1) + 32-byte hash
    payload = bytes([tag, 0]) + bytes(range(32))
    return ton_encode(payload)


def test_ton_address_valid(ton_addr):
    v = TONValidator()
    m = v.validate(_cand(ton_addr))
    assert m is not None
    assert m.chain == "TON"
    assert m.format.startswith("user-friendly")
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_ton_address_starts_with_E_or_U(ton_addr):
    # Bounceable starts with EQ, non-bounceable with UQ
    assert ton_addr.startswith(("EQ", "UQ", "kQ", "0Q"))


def test_invalid_rejected():
    v = TONValidator()
    assert v.validate(_cand("not a ton address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_shape_match(ton_addr):
    v = TONValidator()
    assert v.shape_match(_cand(ton_addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(ton_addr):
    v = TONValidator()
    m = v.validate(_cand(ton_addr))
    assert m is not None
    assert m.cross_chain_alternates == []
