"""Near (NEAR) validator.

Two account ID formats:
  1. Implicit: 64 lowercase hex chars (32-byte Ed25519 pubkey, NO 0x prefix)
  2. Named: human-readable like 'alice.near' or 'example.testnet'

Implicit accounts have no checksum — confidence caps at 50.
Named accounts are very low-confidence (could be many things, but matches
the Near naming pattern).
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match

# Implicit: exactly 64 lowercase hex chars, NO 0x prefix
_IMPLICIT_RE = re.compile(r"^[0-9a-f]{64}$")

# Named: starts/ends with alphanumeric, contains alphanumeric + dashes + dots
# Must end with .near or .testnet (or subaccount of those)
_NAMED_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}[a-z0-9]\.(near|testnet)$")


class NearValidator:
    chain = "NEAR"
    formats = ["implicit-ed25519", "named-account"]

    def shape_match(self, candidate: Candidate) -> bool:
        s = candidate.normalized
        # 0x prefix disqualifies Near implicit
        if s.startswith(("0x", "0X")):
            return False
        return bool(_IMPLICIT_RE.match(s) or _NAMED_RE.match(s))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        # Reject anything with 0x prefix — that's not Near
        if s.startswith(("0x", "0X")):
            return None

        if _IMPLICIT_RE.match(s):
            return Match(
                chain="NEAR",
                format="implicit-ed25519",
                key_type="address",
                confidence=50,
                checksum_status="none",  # no checksum
                network="mainnet",
                cross_chain_alternates=[],
                wallet_compatibility=wallets_for("NEAR"),
                repairs_applied=candidate.repairs,
                notes=["implicit account (32-byte ed25519 pubkey hex)"],
            )

        if _NAMED_RE.match(s):
            return Match(
                chain="NEAR",
                format="named-account",
                key_type="address",
                confidence=20,  # very low — could plausibly be something else
                checksum_status="none",
                network="mainnet" if s.endswith(".near") else "testnet",
                cross_chain_alternates=[],
                wallet_compatibility=wallets_for("NEAR"),
                repairs_applied=candidate.repairs,
                notes=[f"named account ending in .{s.split('.')[-1]}"],
            )

        return None

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
