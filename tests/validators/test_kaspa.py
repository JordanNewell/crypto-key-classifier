import pytest

from ckc.models import Candidate
from ckc.validators.base import bech32_encode, convertbits
from ckc.validators.kaspa import KaspaValidator


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module", params=["kaspa", "kaspatest"])
def kaspa_addr(request) -> str:
    """Generate valid Kaspa addresses for mainnet and testnet."""
    hrp = request.param
    pubkey = bytes(range(32))  # 32-byte Schnorr pubkey
    data_5bit = convertbits(list(pubkey), 8, 5, True)
    return bech32_encode(hrp, data_5bit, "bech32")


def test_kaspa_address_valid(kaspa_addr):
    v = KaspaValidator()
    m = v.validate(_cand(kaspa_addr))
    assert m is not None
    assert m.chain == "KAS"
    assert m.format == "bech32"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_kaspa_mainnet_network(kaspa_addr):
    v = KaspaValidator()
    m = v.validate(_cand(kaspa_addr))
    assert m is not None
    # mainnet for 'kaspa' HRP, testnet for 'kaspatest' HRP
    if kaspa_addr.startswith("kaspatest"):
        assert m.network == "testnet"
    else:
        assert m.network == "mainnet"


def test_invalid_rejected():
    v = KaspaValidator()
    assert v.validate(_cand("not a kaspa address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_shape_match(kaspa_addr):
    v = KaspaValidator()
    assert v.shape_match(_cand(kaspa_addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(kaspa_addr):
    v = KaspaValidator()
    m = v.validate(_cand(kaspa_addr))
    assert m is not None
    assert m.cross_chain_alternates == []
