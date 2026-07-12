import pytest

from ckc.models import Candidate
from ckc.validators.base import bech32_encode, convertbits
from ckc.validators.cosmos import CosmosValidator


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module")
def cosmos_addr() -> str:
    """Generate a known-valid cosmos1 address via bech32_encode."""
    # 20-byte hash → 5-bit groups for bech32
    hash160 = bytes(range(20))  # deterministic test value
    data_5bit = convertbits(list(hash160), 8, 5, True)
    return bech32_encode("cosmos", data_5bit, "bech32")


def test_cosmos_atom_valid(cosmos_addr):
    v = CosmosValidator()
    m = v.validate(_cand(cosmos_addr))
    assert m is not None
    assert m.chain == "ATOM"
    assert m.format == "bech32"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_cross_chain_alternates_populated(cosmos_addr):
    v = CosmosValidator()
    m = v.validate(_cand(cosmos_addr))
    assert m is not None
    chains = [c for c, _ in m.cross_chain_alternates]
    assert "OSMO" in chains
    assert "JUNO" in chains
    assert "AKT" in chains  # akash
    assert len(m.cross_chain_alternates) >= 5


def test_cross_chain_alternates_are_valid_bech32(cosmos_addr):
    """Each alternate must itself be a valid bech32 string (round-trip)."""
    from ckc.validators.base import bech32_decode
    v = CosmosValidator()
    m = v.validate(_cand(cosmos_addr))
    assert m is not None
    for chain, addr in m.cross_chain_alternates:
        decoded = bech32_decode(addr)
        assert decoded is not None, f"{chain} addr {addr} failed bech32 decode"
        # All alternates should decode to the SAME 20-byte hash160 as the input
        hrp, data, spec = decoded
        original = bech32_decode(cosmos_addr)
        assert data == original[1], f"{chain} addr decoded to different data than input"


def test_invalid_rejected():
    v = CosmosValidator()
    assert v.validate(_cand("cosmos1invalid")) is None
    assert v.validate(_cand("not a cosmos address")) is None


def test_shape_match():
    v = CosmosValidator()
    # Generate an osmo address for shape match test
    hash160 = bytes(range(20))
    data_5bit = convertbits(list(hash160), 8, 5, True)
    osmo_addr = bech32_encode("osmo", data_5bit, "bech32")
    assert v.shape_match(_cand(osmo_addr))
    assert not v.shape_match(_cand("0xabc"))
