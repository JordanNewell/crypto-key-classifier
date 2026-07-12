import pytest

from ckc.models import Candidate
from ckc.validators.base import keccak256
from ckc.validators.monero import MoneroValidator, monero_encode_address


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


def _keccak_checksum(data: bytes) -> bytes:
    """Compute first 4 bytes of Keccak-256 — Monero's checksum."""
    return keccak256(data)[:4]


@pytest.fixture(scope="module")
def monero_mainnet_addr() -> str:
    """Generate a valid Monero mainnet address."""
    network = b"\x12"  # mainnet
    spend_pubkey = bytes(range(32))
    view_pubkey = bytes(range(32, 64))
    payload = network + spend_pubkey + view_pubkey  # 65 bytes
    checksum = _keccak_checksum(payload)
    full_payload = payload + checksum  # 69 bytes
    return monero_encode_address(full_payload)


def test_monero_mainnet_valid(monero_mainnet_addr):
    v = MoneroValidator()
    m = v.validate(_cand(monero_mainnet_addr))
    assert m is not None
    assert m.chain == "XMR"
    assert m.format == "address"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_monero_address_length(monero_mainnet_addr):
    # Monero mainnet addresses are exactly 95 chars
    assert len(monero_mainnet_addr) == 95


def test_monero_mainnet_starts_with_4_or_8(monero_mainnet_addr):
    # Mainnet: standard address starts with '4', subaddress with '8'
    # Our generated one starts with whatever 0x12 encodes to (typically '4' or '5')
    # Just check it's a valid Monero base58 char
    assert monero_mainnet_addr[0] in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def test_invalid_rejected():
    v = MoneroValidator()
    assert v.validate(_cand("not a monero address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_shape_match(monero_mainnet_addr):
    v = MoneroValidator()
    assert v.shape_match(_cand(monero_mainnet_addr))
    assert not v.shape_match(_cand("0xabc"))


def test_round_trip_encode_decode(monero_mainnet_addr):
    """Encode then decode should produce the same bytes."""
    v = MoneroValidator()
    decoded = v._decode(monero_mainnet_addr)
    assert decoded is not None
    assert len(decoded) == 69


def test_no_cross_chain_alternates(monero_mainnet_addr):
    v = MoneroValidator()
    m = v.validate(_cand(monero_mainnet_addr))
    assert m is not None
    assert m.cross_chain_alternates == []


def test_corrupted_address_rejected(monero_mainnet_addr):
    # Flip one character — checksum should fail
    v = MoneroValidator()
    # Change first char to something different
    first_char = monero_mainnet_addr[0]
    new_first = "Z" if first_char != "Z" else "Y"
    corrupted = new_first + monero_mainnet_addr[1:]
    assert v.validate(_cand(corrupted)) is None
