"""Sui / Aptos validator.

BOTH chains use 0x + 64 hex (32-byte) addresses. They are STRUCTURALLY
IDENTICAL — we cannot distinguish them by format alone.

The difference is in HOW the address is derived from a public key:
  - Sui:   BLAKE2b(pubkey)
  - Aptos: SHA3-256(pubkey)

This validator reports the address as one chain (SUI as primary, since
alphabetically first) with a note that it could also be APT. Confidence
is capped at 30 (low) due to fundamental ambiguity.
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match

# 0x + 64 hex (32 bytes) — both SUI and APT
_ADDR_RE = re.compile(r"^(0x)?[0-9a-fA-F]{64}$")


class SuiAptosValidator:
    chain = "SUI"  # primary chain tag for registry filtering
    formats = ["blake2b-or-sha3-256-hash"]
    # Both chains this validator can produce (for pipeline filtering)
    chains_covered = {"SUI", "APT"}

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_ADDR_RE.match(candidate.normalized))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _ADDR_RE.match(s):
            return None
        body = s[2:] if s.startswith(("0x", "0X")) else s
        if len(body) != 64:
            return None
        try:
            addr_bytes = bytes.fromhex(body)
        except ValueError:
            return None
        if len(addr_bytes) != 32:
            return None

        # Check for zero bytes (unlikely valid address but technically allowed)
        # Sui/Aptos both allow any 32-byte value

        # Report SUI as primary with ambiguity note
        return Match(
            chain="SUI",
            format="blake2b-or-sha3-256-hash",
            key_type="address",
            confidence=30,  # low — fundamentally ambiguous
            checksum_status="none",  # no checksum exists
            network="mainnet",
            cross_chain_alternates=[],  # ambiguity is structural, not cross-chain
            wallet_compatibility=wallets_for("SUI") + wallets_for("APT"),
            repairs_applied=candidate.repairs,
            notes=[
                "AMBIGUOUS: could be SUI (BLAKE2b of pubkey) OR APT (SHA3-256 of pubkey)",
                "structural format identical — cannot distinguish without context",
            ],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
