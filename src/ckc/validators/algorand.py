"""Algorand (ALGO) validator.

Algorand addresses are 32-byte Ed25519 pubkeys with a 4-byte checksum:
  address_str = base32_encode_unpadded(pubkey + first_4_bytes(SHA512/256(pubkey)))

Total bytes = 36, encoded as base32 RFC4648 WITHOUT padding = exactly 58 chars.
"""

from __future__ import annotations

import base64
import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import sha512_256

# Algorand addresses: base32 RFC4648 unpadded, exactly 58 chars
# Charset: A-Z, 2-7 (RFC4648)
_ALGO_RE = re.compile(r"^[A-Z2-7]{58}$")


def algorand_encode_address(pubkey: bytes) -> str:
    """Encode a 32-byte Ed25519 pubkey as an Algorand address string."""
    if len(pubkey) != 32:
        raise ValueError("pubkey must be 32 bytes")
    checksum = sha512_256(pubkey)[:4]
    raw = pubkey + checksum  # 36 bytes
    # base32 RFC4648 unpadded
    encoded = base64.b32encode(raw).decode("ascii").rstrip("=")
    return encoded


def _algorand_decode_address(s: str) -> bytes | None:
    """Decode an Algorand address. Returns 32-byte pubkey, or None if invalid."""
    try:
        # Re-pad to multiple of 8 chars
        padded = s + "=" * (-len(s) % 8)
        raw = base64.b32decode(padded)
    except Exception:
        return None
    if len(raw) != 36:
        return None
    pubkey, checksum = raw[:32], raw[32:]
    if sha512_256(pubkey)[:4] != checksum:
        return None
    return pubkey


class AlgorandValidator:
    chain = "ALGO"
    formats = ["ed25519-pubkey-base32"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_ALGO_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _ALGO_RE.match(s):
            return None
        pubkey = _algorand_decode_address(s)
        if pubkey is None:
            return None
        return Match(
            chain="ALGO",
            format="ed25519-pubkey-base32",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=[],
            wallet_compatibility=wallets_for("ALGO"),
            repairs_applied=candidate.repairs,
            notes=[],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
