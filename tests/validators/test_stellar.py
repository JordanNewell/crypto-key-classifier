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


@pytest.fixture(scope="module")
def stellar_secret() -> str:
    """Generate a valid Stellar S... secret key.

    Uses version byte 0x90 ('S') + a deterministic 32-byte scalar. This is a
    SYNTHETIC fixture (zeros), not a real mainnet key — same convention as the
    existing account fixture above.
    """
    return stellar_encode(b"\x90" + bytes(32))


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


def test_stellar_secret_valid(stellar_secret):
    """Version byte 0x90 → 'S' prefix → ed25519 secret key (previously uncovered)."""
    v = StellarValidator()
    m = v.validate(_cand(stellar_secret))
    assert m is not None
    assert m.chain == "XLM"
    assert m.format == "ed25519-secret-base32"
    assert m.key_type == "private-key"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_stellar_secret_starts_with_S(stellar_secret):
    # 0x90 version byte encodes as 'S' in base32
    assert stellar_secret.startswith("S")


def test_stellar_secret_length(stellar_secret):
    assert len(stellar_secret) == 56


def test_stellar_unknown_version_byte_rejected():
    """A 56-char base32 string with valid CRC but unknown version byte is rejected.

    Version byte 0x00 isn't G(0x30)/S(0x90)/M(0x60), so validate() returns None
    even after a successful CRC check. Covers the `else: return None` branch.
    """
    v = StellarValidator()
    # 0x00 + 32 zero bytes + valid CRC → 56-char base32 string
    addr = stellar_encode(b"\x00" + bytes(32))
    assert len(addr) == 56
    # shape matches (it's valid base32 of the right length) but version is unknown
    assert v.shape_match(_cand(addr))
    assert v.validate(_cand(addr)) is None


def test_stellar_bad_checksum_rejected(stellar_account):
    """Flip a base32 char so the CRC16-XMODEM check fails — covers the bad-checksum path."""
    v = StellarValidator()
    # Stellar addresses start with 'G' (0x30 in base32). Replace the last char
    # with a different valid base32 char to corrupt the CRC.
    corrupted = stellar_account[:-1] + ("A" if stellar_account[-1] != "A" else "B")
    assert corrupted != stellar_account
    assert v.shape_match(_cand(corrupted))
    assert v.validate(_cand(corrupted)) is None


def test_stellar_non_base32_chars_rejected():
    """Chars outside RFC 4648 base32 alphabet (A-Z, 2-7) fail shape_match → validate → None."""
    v = StellarValidator()
    # 56 chars but contains '0', '1', '8', '9' which are not in the base32 alphabet
    bad = ("G0189ABCDEF" * 5)[:55] + "0"  # 56 chars, invalid base32 chars
    assert len(bad) == 56
    assert not v.shape_match(_cand(bad))
    assert v.validate(_cand(bad)) is None


def test_stellar_too_short_rejected():
    """A base32 string shorter than 56 chars fails the regex shape check."""
    v = StellarValidator()
    short = "GAAAAAA"  # 7 chars, valid base32 but way too short
    assert not v.shape_match(_cand(short))
    assert v.validate(_cand(short)) is None


def test_stellar_invalid_rejected():
    v = StellarValidator()
    assert v.validate(_cand("not a stellar address")) is None
    assert v.validate(_cand("0xabc")) is None


def test_stellar_shape_match(stellar_account):
    v = StellarValidator()
    assert v.shape_match(_cand(stellar_account))
    assert not v.shape_match(_cand("0xabc"))


def test_stellar_no_cross_chain_alternates(stellar_account):
    v = StellarValidator()
    m = v.validate(_cand(stellar_account))
    assert m is not None
    assert m.cross_chain_alternates == []


def test_stellar_cross_chain_encodings_empty(stellar_account):
    """cross_chain_encodings() always returns [] for Stellar (previously uncovered)."""
    v = StellarValidator()
    m = v.validate(_cand(stellar_account))
    assert m is not None
    assert v.cross_chain_encodings(m) == []


def test_stellar_suggest_repairs_empty(stellar_account):
    """Stellar never proposes repairs — confirm the contract holds."""
    v = StellarValidator()
    assert v.suggest_repairs(_cand(stellar_account)) == []
