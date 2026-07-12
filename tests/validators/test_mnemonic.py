from ckc.models import Candidate
from ckc.validators.mnemonic import MnemonicValidator


def _cand(s: str, repairs=None) -> Candidate:
    return Candidate(
        raw=s, normalized=s, repairs=repairs or [], encoding=None, bytes_value=None
    )


# Well-known BIP-39 test vectors (from Trezor python-mnemonic test suite)
# 12-word zero-entropy vector: abandon x11 + about
VALID_12_WORD = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
)
# 24-word zero-entropy vector: abandon x23 + art
VALID_24_WORD = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon art"
)

# "abondon" is one char off from "abandon"
TYPO_12_WORD = (
    "abondon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
)


def test_bip39_12_word_valid():
    v = MnemonicValidator()
    m = v.validate(_cand(VALID_12_WORD))
    assert m is not None
    assert m.chain == "BIP39"
    assert m.format == "mnemonic-12-word"
    assert m.key_type == "mnemonic"
    assert m.checksum_status == "valid"
    assert m.confidence == 100


def test_bip39_24_word_valid():
    v = MnemonicValidator()
    m = v.validate(_cand(VALID_24_WORD))
    assert m is not None
    assert m.format == "mnemonic-24-word"


def test_bip39_invalid_checksum_flagged():
    # 12 "abandon" — last word should be "about" to satisfy checksum
    v = MnemonicValidator()
    invalid = (
        "abandon abandon abandon abandon abandon abandon abandon abandon "
        "abandon abandon abandon abandon"
    )
    m = v.validate(_cand(invalid))
    # Should return a low-confidence match with checksum_status=failed
    if m is not None:
        assert m.checksum_status == "failed"
        assert m.confidence <= 40


def test_shape_match_mnemonic_pattern():
    v = MnemonicValidator()
    assert v.shape_match(_cand(VALID_12_WORD))
    assert v.shape_match(_cand(VALID_24_WORD))


def test_shape_match_non_mnemonic():
    v = MnemonicValidator()
    assert not v.shape_match(_cand("not a mnemonic"))
    assert not v.shape_match(_cand("0xabc"))
    assert not v.shape_match(_cand("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))


def test_typo_repair_via_suggest_repairs():
    """suggest_repairs should propose a fix for the typo'd word."""
    v = MnemonicValidator()
    candidates = v.suggest_repairs(_cand(TYPO_12_WORD))
    # Should produce at least one variant with "abondon" -> "abandon"
    abandon_variants = [
        c for c in candidates if "abandon abandon abandon" in c.normalized[:30]
    ]
    assert len(abandon_variants) > 0
    # Each should note the repair
    assert any(
        "levenshtein" in r.lower() for c in abandon_variants for r in c.repairs
    )


def test_typo_repaired_mnemonic_validates():
    """After repair, the mnemonic should pass BIP-39 validation."""
    v = MnemonicValidator()
    candidates = v.suggest_repairs(_cand(TYPO_12_WORD))
    valid_found = False
    for c in candidates:
        m = v.validate(c)
        if m and m.checksum_status == "valid":
            valid_found = True
            break
    assert valid_found


def test_no_cross_chain_alternates():
    v = MnemonicValidator()
    m = v.validate(_cand(VALID_12_WORD))
    assert m is not None
    assert m.cross_chain_alternates == []


def test_notes_include_derivation_info():
    v = MnemonicValidator()
    m = v.validate(_cand(VALID_12_WORD))
    assert m is not None
    notes_joined = " ".join(m.notes).lower()
    assert (
        "bip39" in notes_joined
        or "bip-39" in notes_joined
        or "derivation" in notes_joined
        or "wallet" in notes_joined
    )


def test_electrum_detection_note_on_checksum_failure():
    """When BIP-39 checksum fails on a wordlist phrase, note 'Electrum' possibility."""
    v = MnemonicValidator()
    # Use a phrase where checksum will fail (12 abandons)
    bad_phrase = (
        "abandon abandon abandon abandon abandon abandon abandon abandon "
        "abandon abandon abandon abandon"
    )
    m = v.validate(_cand(bad_phrase))
    if m is not None and m.checksum_status == "failed":
        notes_joined = " ".join(m.notes).lower()
        assert "electrum" in notes_joined or "alternative" in notes_joined
