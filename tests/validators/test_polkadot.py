import pytest

from ckc.models import Candidate
from ckc.validators.polkadot import PolkadotValidator, ss58_encode


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module", params=[(0, "DOT"), (2, "KSM")])
def ss58_addr(request) -> tuple[str, str]:
    """Generate valid SS58 addresses for Polkadot and Kusama."""
    prefix_byte, expected_chain = request.param
    # 1-byte prefix + 32-byte ed25519 pubkey (most common case)
    pubkey = bytes(range(32))
    addr = ss58_encode(prefix_byte, pubkey)
    return addr, expected_chain


def test_ss58_address_valid(ss58_addr):
    addr, expected_chain = ss58_addr
    v = PolkadotValidator()
    m = v.validate(_cand(addr))
    assert m is not None
    assert m.chain == expected_chain
    assert m.format == "SS58"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_ss58_round_trip():
    # Encode then validate
    pubkey = bytes(range(32))
    encoded = ss58_encode(0, pubkey)
    v = PolkadotValidator()
    m = v.validate(_cand(encoded))
    assert m is not None
    assert m.chain == "DOT"


def test_invalid_rejected():
    v = PolkadotValidator()
    assert v.validate(_cand("not an ss58 address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_shape_match(ss58_addr):
    addr, _ = ss58_addr
    v = PolkadotValidator()
    assert v.shape_match(_cand(addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(ss58_addr):
    addr, _ = ss58_addr
    v = PolkadotValidator()
    m = v.validate(_cand(addr))
    assert m is not None
    assert m.cross_chain_alternates == []
