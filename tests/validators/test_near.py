import pytest

from ckc.validators.near import NearValidator
from ckc.models import Candidate


def _cand(s: str) -> Candidate:
    return Candidate(raw=s, normalized=s, repairs=[], encoding=None, bytes_value=None)


def test_near_implicit_valid():
    # 64 lowercase hex chars (no 0x prefix)
    addr = "a" * 64
    v = NearValidator()
    m = v.validate(_cand(addr))
    assert m is not None
    assert m.chain == "NEAR"
    assert m.format == "implicit-ed25519"
    assert m.confidence == 50  # format-only match, no checksum


def test_near_implicit_lowercase_only():
    # Implicit accounts must be lowercase hex (no uppercase allowed)
    addr = "A" * 64  # uppercase
    v = NearValidator()
    m = v.validate(_cand(addr))
    # Should reject — implicit must be lowercase only
    # OR accept with reduced confidence. Spec: lowercase only.
    assert m is None or m.confidence < 50


def test_near_implicit_no_0x_prefix():
    # Implicit accounts do NOT have 0x prefix
    # If user provides 0x + 64 hex, that's actually ETH private key shape
    addr = "0x" + "a" * 64
    v = NearValidator()
    m = v.validate(_cand(addr))
    # 0x prefix should NOT match Near implicit
    assert m is None


def test_near_named_account():
    addr = "alice.near"
    v = NearValidator()
    m = v.validate(_cand(addr))
    assert m is not None
    assert m.chain == "NEAR"
    assert m.format == "named-account"
    assert m.confidence < 50  # very low confidence — could be many things


def test_invalid_rejected():
    v = NearValidator()
    assert v.validate(_cand("not a near account")) is None
    # "alice.near" pattern but with invalid chars
    assert v.validate(_cand("Alice.near")) is None  # uppercase invalid


def test_shape_match():
    v = NearValidator()
    assert v.shape_match(_cand("a" * 64))
    assert v.shape_match(_cand("alice.near"))
    assert not v.shape_match(_cand("0xabc"))


def test_no_cross_chain_alternates():
    v = NearValidator()
    m = v.validate(_cand("a" * 64))
    assert m is not None
    assert m.cross_chain_alternates == []
