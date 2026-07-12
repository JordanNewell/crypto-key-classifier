from ckc.validators.solana import SolanaValidator
from ckc.models import Candidate


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


def test_solana_address_valid():
    v = SolanaValidator()
    m = v.validate(_cand("dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc"))
    assert m is not None
    assert m.chain == "SOL"
    assert m.checksum_status == "none"  # Solana has no checksum
    assert m.confidence == 50  # capped at 50 — no checksum exists


def test_solana_address_min_length():
    v = SolanaValidator()
    # 32 bytes encoded as base58 = 43-44 chars typically, but can be shorter
    m = v.validate(_cand("11111111111111111111111111111111"))
    assert m is not None


def test_invalid_rejected():
    v = SolanaValidator()
    assert v.validate(_cand("0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318")) is None
    assert v.validate(_cand("too short")) is None


def test_shape_match():
    v = SolanaValidator()
    assert v.shape_match(_cand("dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc"))
    assert not v.shape_match(_cand("0xabc"))
