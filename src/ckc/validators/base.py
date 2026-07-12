"""Validator protocol + shared crypto helpers.

Each chain validator subclasses Validator and implements shape_match,
validate, suggest_repairs, and (optionally) cross_chain_encodings.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import base58
from Crypto.Hash import keccak

from ckc.models import Candidate, Match


class Validator(Protocol):
    """Protocol every validator implements.

    Concrete validators are discovered by validators/__init__.py via pkgutil.
    """

    chain: str
    formats: list[str]

    def shape_match(self, candidate: Candidate) -> bool:
        """Cheap check: right length, charset, prefix? No checksum yet."""
        ...

    def validate(self, candidate: Candidate) -> Match | None:
        """Strict validation: checksum, network byte, etc. Returns None if rejected."""
        ...

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        """Format-specific repair candidates (return [] to defer to generic layer)."""
        ...

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        """For shared-key families: enumerate alternate chain encodings."""
        ...


# --- Shared crypto helpers ---


def keccak256(data: bytes) -> bytes:
    """Keccak-256 hash (NOT SHA3-256 — different padding)."""
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def double_sha256(data: bytes) -> bytes:
    return sha256(sha256(data))


def base58check_encode(payload: bytes) -> str:
    """Encode payload with double-SHA256 checksum (4 bytes)."""
    checksum = double_sha256(payload)[:4]
    return base58.b58encode(payload + checksum).decode("ascii")


def base58check_decode(s: str) -> bytes | None:
    """Decode base58check-encoded string. Returns payload WITHOUT checksum,
    or None if checksum fails."""
    try:
        full = base58.b58decode(s)
    except Exception:
        return None
    if len(full) < 5:
        return None
    payload, checksum = full[:-4], full[-4:]
    if double_sha256(payload)[:4] != checksum:
        return None
    return payload


def bech32_validate(s: str) -> tuple[str, bytes, str] | None:
    """Validate bech32/bech32m string. Returns (hrp, data, variant) or None.

    variant is "bech32" or "bech32m" depending on BIP-173 vs BIP-350.
    """
    import bech32
    # The `bech32` package exposes bech32.bech32_decode / convertbits
    hrp, data, spec = bech32.bech32_decode(s)
    if data is None:
        return None
    spec_name = {bech32.Encoding.BECH32: "bech32", bech32.Encoding.BECH32M: "bech32m"}.get(
        spec, "unknown"
    )
    return (hrp, bytes(data), spec_name)
