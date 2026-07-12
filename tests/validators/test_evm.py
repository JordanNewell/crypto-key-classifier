from ckc.models import Candidate
from ckc.validators.evm import EVMValidator


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


def test_eth_address_valid_eip55():
    v = EVMValidator()
    m = v.validate(_cand("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"))
    assert m is not None
    assert m.chain == "ETH"
    assert m.format == "address-eip55"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_eth_address_lowercase_no_checksum_valid():
    v = EVMValidator()
    m = v.validate(_cand("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"))
    assert m is not None
    assert m.checksum_status == "none"
    assert m.confidence == 50  # no checksum applied, format only


def test_eth_address_bad_checksum_repairable():
    # Last char flipped — EIP-55 fix would correct it
    v = EVMValidator()
    m = v.validate(_cand("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAee"))
    # Should either reject OR return a low-confidence match with repair note
    if m is not None:
        assert m.checksum_status == "failed"


def test_eth_private_key_valid():
    v = EVMValidator()
    m = v.validate(_cand("0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"))
    assert m is not None
    assert m.key_type == "private-key"
    assert m.format == "secp256k1-private-key"


def test_invalid_rejected():
    v = EVMValidator()
    assert v.validate(_cand("0xdeadbeef")) is None  # too short
    assert v.validate(_cand("0xZZZZ")) is None


def test_shape_match():
    v = EVMValidator()
    assert v.shape_match(_cand("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"))
    assert not v.shape_match(_cand("not a key"))
