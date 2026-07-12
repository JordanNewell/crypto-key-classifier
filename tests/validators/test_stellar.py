import pytest

from ckc.models import Candidate
from ckc.validators.stellar import StellarValidator, stellar_encode


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


@pytest.fixture(scope="module")
def stellar_account() -> str:
    """Generate a valid Stellar G... account address."""
    # Version byte 0x30 ('G') + 32-byte ed25519 pubkey
    return stellar_encode(b"\x30" + bytes(range(32)))


def test_stellar_account_valid(stellar_account):
    v = StellarValidator()
    m = v.validate(_cand(stellar_account))
    assert m is not None
    assert m.chain == "XLM"
    assert m.format == "ed25519-account-base32"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_stellar_account_starts_with_G(stellar_account):
    # 0x30 version byte encodes as 'G' in base32
    assert stellar_account.startswith("G")


def test_stellar_account_length(stellar_account):
    # G/S addresses are exactly 56 chars
    assert len(stellar_account) == 56


def test_invalid_rejected():
    v = StellarValidator()
    assert v.validate(_cand("not a stellar address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_shape_match(stellar_account):
    v = StellarValidator()
    assert v.shape_match(_cand(stellar_account))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates(stellar_account):
    v = StellarValidator()
    m = v.validate(_cand(stellar_account))
    assert m is not None
    assert m.cross_chain_alternates == []
