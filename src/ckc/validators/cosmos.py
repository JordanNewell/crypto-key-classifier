"""Cosmos validator: IBC family cross-chain.

All Cosmos SDK chains use the same secp256k1 keypair, derived via
m/44'/118'/0'/0/0. The 20-byte pubkey hash is bech32-encoded with
different HRPs per chain. ONE decode → N re-encodings.

This is the headline 'crafty' feature: paste a cosmos1... address,
get back 9+ alternate encodings for Osmosis, Juno, Akash, etc.
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import bech32_decode, bech32_encode

# HRP → canonical chain code. Order matters for "primary" identification.
_HRPS: list[tuple[str, str]] = [
    ("cosmos", "ATOM"),
    ("osmo", "OSMO"),
    ("juno", "JUNO"),
    ("akash", "AKT"),
    ("inj", "INJ"),
    ("evmos", "EVMOS"),
    ("stride", "STRD"),
    ("regen", "REGEN"),
    ("persistence", "XPRT"),
    ("secret", "SCRT"),
    ("kava", "KAVA"),
    ("cro", "CRO"),
    ("terra", "LUNA"),
    ("band", "BAND"),
    ("umee", "UMEE"),
    ("stars", "STARS"),
    ("sent", "DVPN"),
    ("like", "LIKE"),
    ("axelar", "AXL"),
    ("cre", "CRE"),
]

_HRP_TO_CHAIN: dict[str, str] = dict(_HRPS)
_CHAIN_TO_HRP: dict[str, str] = {v: k for k, v in _HRPS}

# Match any of the known HRPs at start of bech32 string
_HRP_RE = re.compile(r"^(" + "|".join(h for h, _ in _HRPS) + r")1[02-9ac-hj-np-z]{38}")


class CosmosValidator:
    chain = "COSMOS_FAMILY"  # per-match chain is more specific
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
        hrp, data, spec = result
        # Cosmos addresses use bech32 (not bech32m)
        if spec != "bech32":
            return None

        # Generate cross-chain alternates by re-encoding with other HRPs
        alternates: list[tuple[str, str]] = []
        for alt_chain in _CHAIN_TO_HRP:
            if alt_chain == _HRP_TO_CHAIN.get(hrp):
                continue
            alt_hrp = _CHAIN_TO_HRP[alt_chain]
            reencoded = bech32_encode(alt_hrp, data, "bech32")
            alternates.append((alt_chain, reencoded))

        chain = _HRP_TO_CHAIN.get(hrp)
        if chain is None:
            return None

        return Match(
            chain=chain,
            format="bech32",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=alternates,
            wallet_compatibility=wallets_for(chain),
            repairs_applied=candidate.repairs,
            notes=[f"same key works on {len(_HRPS)} Cosmos chains (HRP swap)"],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return match.cross_chain_alternates
