"""Kaspa (KAS) validator.

Kaspa uses bech32 with HRP 'kaspa' (mainnet) or 'kaspatest' (testnet).
Body = 32-byte Schnorr pubkey (secp256k1).
Uses bech32 (NOT bech32m).
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import bech32_decode

# Match kaspa or kaspatest HRP + bech32 separator + data (32-byte pubkey = ~58 chars bech32)
_KASPA_RE = re.compile(r"^(kaspa|kaspatest)1[02-9ac-hj-np-z]{58,63}$")

_HRPS: dict[str, tuple[str, str]] = {
    "kaspa": ("KAS", "mainnet"),
    "kaspatest": ("KAS", "testnet"),
}


class KaspaValidator:
    chain = "KAS"
    formats = ["bech32"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_KASPA_RE.match(candidate.normalized.lower()))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized.lower()
        if not _KASPA_RE.match(s):
            return None
        result = bech32_decode(s)
        if result is None:
            return None
        hrp, _, spec = result
        if spec != "bech32":
            return None
        if hrp not in _HRPS:
            return None
        chain, network = _HRPS[hrp]
        return Match(
            chain=chain,
            format="bech32",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network=network,
            cross_chain_alternates=[],
            wallet_compatibility=wallets_for(chain),
            repairs_applied=candidate.repairs,
            notes=[f"HRP: {hrp}"],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
