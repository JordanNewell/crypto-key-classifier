"""Tron (TRX) validator.

Tron addresses are 0x41 (version byte) + 20-byte Keccak-256 hash of pubkey
+ 4-byte double-SHA256 checksum, base58check-encoded. Always 34 chars,
always starts with 'T' on mainnet.

Same base58check machinery as Bitcoin, just a different version byte.
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import base58check_decode

# Tron addresses are 34 base58 chars starting with T
_TRON_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")


class TronValidator:
    chain = "TRX"
    formats = ["base58check"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_TRON_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _TRON_RE.match(s):
            return None
        payload = base58check_decode(s)
        if payload is None:
            return None
        # Payload should be: 0x41 prefix + 20-byte hash = 21 bytes total
        if len(payload) != 21:
            return None
        if payload[:1] != b"\x41":
            return None
        return Match(
            chain="TRX",
            format="base58check",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=[],  # Tron key is Tron-only
            wallet_compatibility=wallets_for("TRX"),
            repairs_applied=candidate.repairs,
            notes=[],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
