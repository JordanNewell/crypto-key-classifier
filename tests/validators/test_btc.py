import pytest

from ckc.validators.btc import BTCValidator
from ckc.validators.base import base58check_encode
from ckc.models import Candidate


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


# --- Generated fixtures (symmetric with production code) ---
# Generate valid LTC/DOGE/BCH addresses by encoding zero-hash160 with the
# right version byte. This tests decode-against-encode symmetry, which is
# rigorous for checksum verification.
@pytest.fixture(scope="module")
def ltc_p2pkh_addr() -> str:
    return base58check_encode(b"\x30" + b"\x00" * 20)


@pytest.fixture(scope="module")
def doge_p2pkh_addr() -> str:
    return base58check_encode(b"\x1e" + b"\x00" * 20)


@pytest.fixture(scope="module")
def btc_wif_compressed() -> str:
    # WIF: 0x80 prefix + 32-byte key + 0x01 compressed flag
    return base58check_encode(b"\x80" + b"\x01" * 32 + b"\x01")


def test_p2pkh_btc_valid():
    # Genesis block address — well-known valid P2PKH
    v = BTCValidator()
    m = v.validate(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    assert m is not None
    assert m.chain == "BTC"
    assert m.format == "P2PKH"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_p2pkh_ltc_valid(ltc_p2pkh_addr):
    v = BTCValidator()
    m = v.validate(_cand(ltc_p2pkh_addr))
    assert m is not None
    assert m.chain == "LTC"
    assert m.format == "P2PKH"
    assert m.cross_chain_alternates  # BTC family alternates populated


def test_p2pkh_doge_valid(doge_p2pkh_addr):
    v = BTCValidator()
    m = v.validate(_cand(doge_p2pkh_addr))
    assert m is not None
    assert m.chain == "DOGE"


def test_bech32_segwit_v0_valid():
    # BIP-173 reference test vector
    v = BTCValidator()
    m = v.validate(_cand("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"))
    assert m is not None
    assert m.format == "bech32-segwit-v0"
    assert m.checksum_status == "valid"


def test_bech32m_taproot_valid():
    # BIP-350 reference test vector
    v = BTCValidator()
    m = v.validate(_cand("bc1p5cyxnuxmeuwuvkwfem96lqzszd02n6xdcjrs20cac6yqjjwudpxqkedrcr"))
    assert m is not None
    assert m.format == "taproot-v1"


def test_wif_compressed_valid(btc_wif_compressed):
    v = BTCValidator()
    m = v.validate(_cand(btc_wif_compressed))
    assert m is not None
    assert m.chain == "BTC"
    assert m.format == "WIF-compressed"
    assert m.key_type == "private-key"


def test_invalid_rejected():
    v = BTCValidator()
    # Same shape as genesis address but last char swapped — checksum will fail
    assert v.validate(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfXX")) is None
    assert v.validate(_cand("not a key at all")) is None


def test_shape_match_true_for_plausible():
    v = BTCValidator()
    assert v.shape_match(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))
    assert v.shape_match(_cand("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"))


def test_shape_match_false_for_wrong_charset():
    v = BTCValidator()
    assert not v.shape_match(_cand("0x1234567890abcdef"))  # ETH-ish
    assert not v.shape_match(_cand("hello world"))
