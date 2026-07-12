import pytest

from ckc.models import Candidate
from ckc.validators.base import bech32_encode, convertbits
from ckc.validators.cardano import CardanoValidator


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module", params=["addr1", "stake1", "addr_test1"])
def cardano_addr(request) -> str:
    """Generate valid Cardano bech32 addresses for each HRP."""
    hrp = request.param
    # 57-byte Shelley address (header + 28-byte payment cred + 28-byte stake cred)
    # For simplicity, use 28 bytes which encodes to ~47 chars
    payload = bytes(range(28))
    data_5bit = convertbits(list(payload), 8, 5, True)
    return bech32_encode(hrp, data_5bit, "bech32")


def test_cardano_address_valid(cardano_addr):
    v = CardanoValidator()
    m = v.validate(_cand(cardano_addr))
    assert m is not None
    assert m.chain == "ADA"
    assert m.format == "bech32"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_cardano_addr1_mainnet():
    # Generate a known addr1 address
    payload = bytes(range(28))
    data_5bit = convertbits(list(payload), 8, 5, True)
    addr = bech32_encode("addr1", data_5bit, "bech32")
    v = CardanoValidator()
    m = v.validate(_cand(addr))
    assert m is not None
    assert m.network == "mainnet"


def test_cardano_addr_test1_testnet():
    payload = bytes(range(28))
    data_5bit = convertbits(list(payload), 8, 5, True)
    addr = bech32_encode("addr_test1", data_5bit, "bech32")
    v = CardanoValidator()
    m = v.validate(_cand(addr))
    assert m is not None
    assert m.network == "testnet"


def test_invalid_rejected():
    v = CardanoValidator()
    assert v.validate(_cand("not a cardano address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_shape_match():
    payload = bytes(range(28))
    data_5bit = convertbits(list(payload), 8, 5, True)
    addr = bech32_encode("addr1", data_5bit, "bech32")
    v = CardanoValidator()
    assert v.shape_match(_cand(addr))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(cardano_addr):
    v = CardanoValidator()
    m = v.validate(_cand(cardano_addr))
    assert m is not None
    assert m.cross_chain_alternates == []
