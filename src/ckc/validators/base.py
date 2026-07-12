"""Validator protocol + shared crypto helpers.

Each chain validator subclasses Validator and implements shape_match,
validate, suggest_repairs, and (optionally) cross_chain_encodings.

Bech32/bech32m (BIP-173 + BIP-350) is embedded directly from the official
reference implementation to avoid external package API mismatches.
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


# --- Bech32 / Bech32m (BIP-173 + BIP-350) ---
# Adapted from official reference: https://github.com/sipa/bech32/blob/master/ref/python/segwit_addr.py

BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32M_CONST = 0x2bc830a3


def _bech32_polymod(values: list[int]) -> int:
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_verify_checksum(hrp: str, data: list[int]) -> str | None:
    """Return 'bech32', 'bech32m', or None if checksum invalid."""
    const = _bech32_polymod(_bech32_hrp_expand(hrp) + data)
    if const == 1:
        return "bech32"
    if const == BECH32M_CONST:
        return "bech32m"
    return None


def _bech32_create_checksum(hrp: str, data: list[int], spec: str) -> list[int]:
    const = 0 if spec == "bech32" else BECH32M_CONST
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ const
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def bech32_encode(hrp: str, data: list[int], spec: str = "bech32") -> str:
    """Encode hrp + 5-bit data values with bech32 or bech32m checksum."""
    combined = data + _bech32_create_checksum(hrp, data, spec)
    return hrp + "1" + "".join([BECH32_CHARSET[d] for d in combined])


def bech32_decode(bech: str) -> tuple[str, list[int], str] | None:
    """Decode a bech32(bech32m) string. Returns (hrp, data, spec) or None."""
    if any(ord(x) < 33 or ord(x) > 126 for x in bech):
        return None
    if bech.lower() != bech and bech.upper() != bech:
        return None
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
        return None
    if not all(x in BECH32_CHARSET for x in bech[pos + 1:]):
        return None
    hrp = bech[:pos]
    data = [BECH32_CHARSET.find(x) for x in bech[pos + 1:]]
    spec = _bech32_verify_checksum(hrp, data)
    if spec is None:
        return None
    return (hrp, data[:-6], spec)


def convertbits(data: list[int], frombits: int, tobits: int, pad: bool = True) -> list[int] | None:
    """Convert between bit group sizes (e.g. 8-bit bytes ↔ 5-bit bech32 groups)."""
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def bech32_validate(s: str) -> tuple[str, bytes, str] | None:
    """Validate bech32/bech32m string. Returns (hrp, 5-bit-data, variant) or None.

    variant is 'bech32' or 'bech32m' depending on BIP-173 vs BIP-350.
    Note: data is returned as the raw 5-bit values (list[int] converted to bytes).
    Callers wanting 8-bit bytes must call convertbits() themselves.
    """
    result = bech32_decode(s)
    if result is None:
        return None
    hrp, data, spec = result
    return (hrp, bytes(data), spec)
