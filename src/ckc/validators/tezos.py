"""Tezos (XTZ) validator.

Tezos uses standard Bitcoin base58check encoding with specific 3-byte prefix
bytes that produce recognizable 4-char string prefixes. Each prefix corresponds
to a different signing curve:

  tz1 (06a19f) → Ed25519
  tz2 (06a1a1) → secp256k1
  tz3 (06a1a4) → P-256 (secp256r1)
  tz4 (06a1a0) → BLS12-381

Addresses are 3-byte prefix + 20-byte Blake2b PKH + 4-byte checksum = 36 chars.
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import base58check_decode

# Tezos address shape: tz1/tz2/tz3/tz4 followed by 33 base58 chars = 36 total
_TEZOS_RE = re.compile(r"^tz[1-4][1-9A-HJ-NP-Za-km-z]{33}$")

# Prefix bytes (3 bytes) → (string prefix, signing curve, format detail)
_TEZOS_PREFIXES: dict[bytes, tuple[str, str, str]] = {
    bytes.fromhex("06a19f"): ("tz1", "Ed25519", "ed25519-public-key-hash"),
    bytes.fromhex("06a1a1"): ("tz2", "secp256k1", "secp256k1-public-key-hash"),
    bytes.fromhex("06a1a4"): ("tz3", "P-256", "p256-public-key-hash"),
    bytes.fromhex("06a1a0"): ("tz4", "BLS12-381", "bls12-381-public-key-hash"),
}


class TezosValidator:
    chain = "XTZ"
    formats = ["base58check"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_TEZOS_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _TEZOS_RE.match(s):
            return None
        payload = base58check_decode(s)
        if payload is None:
            return None
        # Payload: 3-byte prefix + 20-byte PKH = 23 bytes
        if len(payload) != 23:
            return None
        prefix_bytes = payload[:3]
        if prefix_bytes not in _TEZOS_PREFIXES:
            return None
        string_prefix, curve, format_detail = _TEZOS_PREFIXES[prefix_bytes]
        return Match(
            chain="XTZ",
            format="base58check",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=[],
            wallet_compatibility=wallets_for("XTZ"),
            repairs_applied=candidate.repairs,
            notes=[f"prefix: {string_prefix}", f"curve: {curve}"],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
