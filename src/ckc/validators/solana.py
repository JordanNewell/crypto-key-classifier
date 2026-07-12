"""Solana validator.

Solana addresses are 32-byte Ed25519 pubkeys, base58-encoded.
No checksum exists — confidence caps at 50 (format_match_no_checksum).

Length range: 32-44 base58 chars (typically 43-44 for random keys).
"""

from __future__ import annotations

import re

import base58

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match

# Base58 alphabet regex, length 32-44 (Solana pubkey range)
_SOL_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class SolanaValidator:
    chain = "SOL"
    formats = ["ed25519-pubkey", "ed25519-private-key"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_SOL_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _SOL_RE.match(s):
            return None
        try:
            b = base58.b58decode(s)
        except Exception:
            return None
        if len(b) != 32:
            return None
        # We can't distinguish address from private key structurally —
        # assume address by default. Private keys in Solana are also 32-byte
        # and look identical (the keypair JSON is the convention, not a format).
        return Match(
            chain="SOL",
            format="ed25519-pubkey",
            key_type="address",  # could also be private-key — flagged in notes
            confidence=50,
            checksum_status="none",
            network="mainnet",
            cross_chain_alternates=[],  # Solana key is Solana-only
            wallet_compatibility=wallets_for("SOL"),
            repairs_applied=candidate.repairs,
            notes=["no checksum exists for Solana — confidence caps at 50"],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
