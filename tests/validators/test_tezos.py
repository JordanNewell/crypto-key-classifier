import pytest

from ckc.models import Candidate
from ckc.validators.base import base58check_encode
from ckc.validators.tezos import TezosValidator


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


# Tezos prefix bytes (3 bytes) — produce recognizable tz1/tz2/tz3/tz4 string prefixes
_TEZOS_PREFIXES = {
    "tz1": bytes.fromhex("06a19f"),  # Ed25519
    "tz2": bytes.fromhex("06a1a1"),  # secp256k1
    "tz3": bytes.fromhex("06a1a4"),  # P-256
    "tz4": bytes.fromhex("06a1a0"),  # BLS12-381
}


@pytest.fixture(scope="module", params=list(_TEZOS_PREFIXES.keys()))
def tezos_addr(request) -> str:
    """Generate valid Tezos addresses for each prefix type."""
    prefix_name = request.param
    prefix_bytes = _TEZOS_PREFIXES[prefix_name]
    # 3-byte prefix + 20-byte Blake2b PKH = 23 bytes
    return base58check_encode(prefix_bytes + bytes(range(20)))


def test_tezos_address_valid(tezos_addr):
    v = TezosValidator()
    m = v.validate(_cand(tezos_addr))
    assert m is not None
    assert m.chain == "XTZ"
    assert m.format == "base58check"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_tezos_prefix_recognized(tezos_addr):
    # Each address should start with tz1, tz2, tz3, or tz4
    assert tezos_addr[:3] in {"tz1", "tz2", "tz3", "tz4"}


def test_invalid_rejected():
    v = TezosValidator()
    assert v.validate(_cand("not a tezos address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_shape_match():
    # Generate a tz1 address
    addr = base58check_encode(_TEZOS_PREFIXES["tz1"] + bytes(range(20)))
    v = TezosValidator()
    assert v.shape_match(_cand(addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates():
    addr = base58check_encode(_TEZOS_PREFIXES["tz1"] + bytes(range(20)))
    v = TezosValidator()
    m = v.validate(_cand(addr))
    assert m is not None
    assert m.cross_chain_alternates == []


def test_curve_type_noted():
    """Validator should note which curve the prefix corresponds to."""
    addr = base58check_encode(_TEZOS_PREFIXES["tz1"] + bytes(range(20)))
    v = TezosValidator()
    m = v.validate(_cand(addr))
    assert m is not None
    notes_joined = " ".join(m.notes)
    assert "Ed25519" in notes_joined or "tz1" in notes_joined
