"""Cardano (ADA) validator.

Two formats:
  1. Shelley-era bech32 with HRPs: addr1 (mainnet payment), stake1 (reward),
     addr_test1 (testnet). Body = header byte + 28-byte payment credential +
     optional 28-byte stake credential.
  2. Byron-era base58 starting with 'DdzFFz' (legacy). NOT in scope for MVP
     of this validator — flag as future work.

Cardano uses bech32 (NOT bech32m) per CIP-19.
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import bech32_decode

# HRP → (chain, network)
_HRPS: dict[str, tuple[str, str]] = {
    "addr1": ("ADA", "mainnet"),
    "stake1": ("ADA", "mainnet"),
    "addr_test1": ("ADA", "testnet"),
    "stake_test1": ("ADA", "testnet"),
}

# Match addr1/stake1/addr_test1/stake_test1 + '1' separator + bech32 data
_HRP_RE = re.compile(
    r"^(addr1|stake1|addr_test1|stake_test1)1[02-9ac-hj-np-z]{6,}$"
)


class CardanoValidator:
    chain = "ADA"
    formats = ["bech32"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_HRP_RE.match(candidate.normalized.lower()))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized.lower()
        if not _HRP_RE.match(s):
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
        key_type = "address" if hrp.startswith("addr") else "reward-account"
        return Match(
            chain=chain,
            format="bech32",
            key_type=key_type,
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
