"""TON validator.

TON "user-friendly" address format:
  tag(1) + workchain(1, signed) + 32-byte state hash + 2-byte CRC16-XMODEM
  → base64 (standard or url-safe)

Tags:
  0x11 → bounceable mainnet  (prefix 'EQ')
  0x51 → non-bounceable mainnet  (prefix 'UQ')
  0x80 bit ORed → testnet  (prefix 'kQ' for bounceable, '0Q' for non-bounceable)

Length: 36 bytes → base64 → 48 chars (36 % 3 == 0, so no padding).
"""

from __future__ import annotations

import base64
import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import crc16_xmodem

# TON user-friendly addresses: 36 bytes → base64 → 48 chars (no padding since 36%3==0).
# Allow either url-safe (-_) or standard (+/) base64 charset, with optional padding.
# Prefix: E/k (bounceable mainnet/testnet) or U/0 (non-bounceable mainnet/testnet),
# always followed by 'Q' (this is a base64 artifact of the tag byte).
_TON_RE = re.compile(r"^[EUk0]Q[A-Za-z0-9+/_-]{46}={0,2}$")


def ton_encode(payload_with_tag_workchain_hash: bytes) -> str:
    """Encode tag+workchain+hash as a TON user-friendly address.
    Caller includes tag(1) + workchain(1) + 32-byte hash = 34 bytes.
    CRC16-XMODEM checksum appended automatically.
    """
    checksum = crc16_xmodem(payload_with_tag_workchain_hash).to_bytes(2, "big")
    full = payload_with_tag_workchain_hash + checksum  # 36 bytes
    # Use URL-safe base64 without padding (TON convention)
    return base64.urlsafe_b64encode(full).decode("ascii").rstrip("=")


def _ton_decode(s: str) -> bytes | None:
    """Decode a TON address. Returns tag+workchain+hash (no checksum) or None."""
    # Try both url-safe and standard base64
    raw: bytes | None = None
    for variant in [s, s.replace("-", "+").replace("_", "/")]:
        try:
            padded = variant + "=" * (-len(variant) % 4)
            decoded = base64.b64decode(padded)
            if len(decoded) == 36:
                raw = decoded
                break
        except Exception:
            continue
    if raw is None:
        return None
    payload, checksum = raw[:-2], raw[-2:]
    expected = crc16_xmodem(payload).to_bytes(2, "big")
    if checksum != expected:
        return None
    return payload


class TONValidator:
    chain = "TON"
    formats = ["user-friendly-bounceable", "user-friendly-non-bounceable"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_TON_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _TON_RE.match(s):
            return None
        payload = _ton_decode(s)
        if payload is None:
            return None
        if len(payload) != 34:
            return None
        tag = payload[0]
        is_testnet = bool(tag & 0x80)
        tag_low = tag & 0x7F
        if tag_low == 0x11:
            bounceable = True
            fmt = "user-friendly-bounceable"
        elif tag_low == 0x51:
            bounceable = False
            fmt = "user-friendly-non-bounceable"
        else:
            return None
        network = "testnet" if is_testnet else "mainnet"
        notes = []
        if is_testnet:
            notes.append("testnet")
        notes.append("bounceable" if bounceable else "non-bounceable")
        return Match(
            chain="TON",
            format=fmt,
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network=network,
            cross_chain_alternates=[],
            wallet_compatibility=wallets_for("TON"),
            repairs_applied=candidate.repairs,
            notes=notes,
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
