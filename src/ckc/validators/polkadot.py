"""Polkadot (DOT/KSM) SS58 validator.

SS58 format: Base58( prefix_byte(s) | pubkey | checksum )

Prefix byte identifies the network:
  0  → Polkadot (DOT)
  2  → Kusama (KSM)
  (many others exist for parachains)

Checksum = first N bytes of Blake2b-512(b"SS58PRE" + payload), where:
  payload length ≤ 32 bytes  → 2-byte checksum
  payload length 33-37 bytes → 3-byte checksum
  payload length ≥ 38 bytes  → 4-byte checksum

Most common case: 1-byte prefix + 32-byte ed25519 pubkey = 33 bytes payload → 2-byte checksum.
Total encoded: 35 bytes base58 → ~46-47 chars.
"""

from __future__ import annotations

import re

import base58

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import blake2b

_SS58PRE = b"SS58PRE"

# Polkadot and Kusama are the most common; full list at https://github.com/paritytech/substrate/blob/master/ss58-registry.json
_PREFIX_TO_CHAIN: dict[int, str] = {
    0: "DOT",
    2: "KSM",
    # Add more as needed: 1 = Polkadot raw, 5 = Alphanumeric suffix, etc.
}

# SS58 addresses use base58 charset, length range covers most common cases
# (35-byte decoded = 33 payload + 2 checksum, or 36 bytes = 33 payload + 3 checksum)
# Base58 encoding varies in length due to leading zero compression
_SS58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{45,49}$")


def _ss58_checksum_length(payload_len: int) -> int:
    """Return checksum length in bytes based on payload length."""
    if payload_len <= 32:
        return 2
    elif payload_len <= 37:
        return 3
    else:
        return 4


def ss58_encode(prefix: int, pubkey: bytes) -> str:
    """Encode a Polkadot SS58 address.
    prefix: network prefix byte (0=Polkadot, 2=Kusama, etc.)
    pubkey: ed25519 or sr25519 pubkey (32 bytes typically)
    """
    if not (0 <= prefix <= 255):
        # For now, only support single-byte prefixes
        raise ValueError("only single-byte prefixes supported")
    payload = bytes([prefix]) + pubkey
    checksum_len = _ss58_checksum_length(len(payload))
    checksum = blake2b(_SS58PRE + payload, digest_size=64)[:checksum_len]
    full = payload + checksum
    return base58.b58encode(full).decode("ascii")


def _ss58_decode(s: str) -> tuple[int, bytes] | None:
    """Decode an SS58 address. Returns (prefix, pubkey) or None if invalid."""
    try:
        full = base58.b58decode(s)
    except Exception:
        return None
    if len(full) < 5:
        return None
    # Try to identify payload/checksum split
    # Most common: prefix(1) + pubkey(32) + checksum(2) = 35 bytes
    # Try the standard case first
    for pubkey_len in [32, 33]:
        payload_len = 1 + pubkey_len
        checksum_len = _ss58_checksum_length(payload_len)
        total = payload_len + checksum_len
        if len(full) != total:
            continue
        prefix_byte = full[0]
        payload = full[:payload_len]
        pubkey = full[1:payload_len]
        checksum = full[payload_len:]
        expected = blake2b(_SS58PRE + payload, digest_size=64)[:checksum_len]
        if checksum == expected:
            return (prefix_byte, pubkey)
    return None


class PolkadotValidator:
    chain = "DOT_FAMILY"  # per-match chain is more specific
    formats = ["SS58"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_SS58_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _SS58_RE.match(s):
            return None
        decoded = _ss58_decode(s)
        if decoded is None:
            return None
        prefix_byte, pubkey = decoded
        chain = _PREFIX_TO_CHAIN.get(prefix_byte, "DOT_UNKNOWN")
        return Match(
            chain=chain,
            format="SS58",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=[],
            wallet_compatibility=wallets_for(chain) if chain != "DOT_UNKNOWN" else [],
            repairs_applied=candidate.repairs,
            notes=[f"SS58 prefix: {prefix_byte}", f"pubkey length: {len(pubkey)}"],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
