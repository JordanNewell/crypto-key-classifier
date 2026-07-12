"""Ripple (XRP) validator.

Ripple uses base58check with a CUSTOM alphabet (different from Bitcoin's).
The alphabet is: rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz

Address format: 0x00 prefix + 20-byte hash + 4-byte double-SHA256 checksum,
encoded with the Ripple alphabet. Mainnet addresses always start with 'r'.
"""

from __future__ import annotations

import hashlib
import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match

# Ripple's custom base58 alphabet (NOT the same as Bitcoin's)
_RIPPLE_ALPHABET = "rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"
_RIPPLE_INDEX = {c: i for i, c in enumerate(_RIPPLE_ALPHABET)}

# Ripple addresses: 25-35 chars, always starts with 'r' on mainnet
_RIPPLE_RE = re.compile(r"^r[rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz]{24,34}$")


def _double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def ripple_base58_encode(data: bytes) -> str:
    """Encode bytes using Ripple's custom base58 alphabet."""
    num = int.from_bytes(data, "big")
    chars = []
    while num > 0:
        num, rem = divmod(num, 58)
        chars.append(_RIPPLE_ALPHABET[rem])
    # Add leading zero bytes as 'r' (the first char of Ripple alphabet)
    leading_zeros = 0
    for b in data:
        if b == 0:
            leading_zeros += 1
        else:
            break
    return "r" * leading_zeros + "".join(reversed(chars))


def ripple_base58_decode(s: str) -> bytes:
    """Decode a Ripple base58-encoded string."""
    num = 0
    for ch in s:
        if ch not in _RIPPLE_INDEX:
            raise ValueError(f"invalid char {ch!r}")
        num = num * 58 + _RIPPLE_INDEX[ch]
    # Convert to bytes
    if num == 0:
        byte_len = 0
    else:
        byte_len = (num.bit_length() + 7) // 8
    decoded = num.to_bytes(byte_len, "big")
    # Add back leading zeros (encoded as 'r' prefix)
    leading_zeros = 0
    for ch in s:
        if ch == "r":
            leading_zeros += 1
        else:
            break
    return b"\x00" * leading_zeros + decoded


def ripple_base58check_encode(payload: bytes) -> str:
    """Encode payload with double-SHA256 checksum using Ripple's alphabet."""
    checksum = _double_sha256(payload)[:4]
    return ripple_base58_encode(payload + checksum)


def ripple_base58check_decode(s: str) -> bytes | None:
    """Decode Ripple base58check string. Returns payload without checksum, or None."""
    try:
        full = ripple_base58_decode(s)
    except Exception:
        return None
    if len(full) < 5:
        return None
    payload, checksum = full[:-4], full[-4:]
    if _double_sha256(payload)[:4] != checksum:
        return None
    return payload


class RippleValidator:
    chain = "XRP"
    formats = ["base58check"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_RIPPLE_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _RIPPLE_RE.match(s):
            return None
        payload = ripple_base58check_decode(s)
        if payload is None:
            return None
        # Payload should be: 0x00 prefix + 20-byte hash = 21 bytes
        if len(payload) != 21:
            return None
        if payload[:1] != b"\x00":
            return None
        return Match(
            chain="XRP",
            format="base58check",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=[],
            wallet_compatibility=wallets_for("XRP"),
            repairs_applied=candidate.repairs,
            notes=[],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
