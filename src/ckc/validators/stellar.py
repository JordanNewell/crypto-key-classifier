"""Stellar (XLM) validator.

Stellar encodes:
  version_byte(1) + payload(32 for accounts) + CRC16-XMODEM(2)
  → base32 RFC4648 UNPADDED

Version bytes:
  0x30 → 'G' prefix (account)
  0x90 → 'S' prefix (secret key)
  0x60 → 'M' prefix (muxed account, SEP-23)

Account/secret addresses are 56 chars; muxed are 69.
"""

from __future__ import annotations

import base64
import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import crc16_xmodem

# Stellar addresses: base32 RFC4648 unpadded, 56 chars for G/S
# Base32 charset: A-Z, 2-7 (RFC4648)
_STELLAR_RE = re.compile(r"^[A-Z2-7]{56}$")


def stellar_encode(payload_with_version: bytes) -> str:
    """Encode version_byte + payload as a Stellar address.
    The caller is responsible for including the version byte at the start.
    CRC16-XMODEM checksum is appended automatically.
    """
    checksum = crc16_xmodem(payload_with_version).to_bytes(2, "big")
    full = payload_with_version + checksum
    return base64.b32encode(full).decode("ascii").rstrip("=")


def _stellar_decode(s: str) -> bytes | None:
    """Decode a Stellar address. Returns version+payload (no checksum) or None."""
    try:
        padded = s + "=" * (-len(s) % 8)
        full = base64.b32decode(padded)
    except Exception:
        return None
    if len(full) < 3:
        return None
    payload, checksum = full[:-2], full[-2:]
    expected = crc16_xmodem(payload).to_bytes(2, "big")
    if checksum != expected:
        return None
    return payload


class StellarValidator:
    chain = "XLM"
    formats = ["ed25519-account-base32", "ed25519-secret-base32"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_STELLAR_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _STELLAR_RE.match(s):
            return None
        payload = _stellar_decode(s)
        if payload is None:
            return None
        version_byte = payload[:1]
        if version_byte == b"\x30":
            key_type = "address"
            fmt = "ed25519-account-base32"
            network = "mainnet"
        elif version_byte == b"\x90":
            key_type = "private-key"
            fmt = "ed25519-secret-base32"
            network = "mainnet"
        else:
            return None
        return Match(
            chain="XLM",
            format=fmt,
            key_type=key_type,
            confidence=100,
            checksum_status="valid",
            network=network,
            cross_chain_alternates=[],
            wallet_compatibility=wallets_for("XLM"),
            repairs_applied=candidate.repairs,
            notes=[],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
