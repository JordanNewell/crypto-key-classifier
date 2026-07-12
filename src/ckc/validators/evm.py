"""EVM validator: ETH + all EVM L2s share identical address/key format.

ETH addresses are 20-byte Keccak-256 hashes, hex-encoded with 0x prefix.
EIP-55 mixed-case checksum adds ~15 bits of corruption detection.

Private keys are 32-byte secp256k1 scalars, hex-encoded with optional 0x.

All EVM L2s (Polygon, Arbitrum, Base, Optimism, BSC, Avalanche, etc.)
use the SAME address format. Cross-chain expansion is chain-ID-only;
the address string is identical, so we list compatible chains.
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import keccak256

# 0x + 40 hex (address) OR 0x + 64 hex (private key) OR raw hex without 0x
_ADDR_RE = re.compile(r"^(0x)?[0-9a-fA-F]{40}$")
_PRIV_RE = re.compile(r"^(0x)?[0-9a-fA-F]{64}$")

# Major EVM chains (chain IDs per EIP-155)
EVM_CHAINS: list[tuple[str, int]] = [
    ("ETH", 1),
    ("Polygon", 137),
    ("Arbitrum", 42161),
    ("Base", 8453),
    ("Optimism", 10),
    ("BSC", 56),
    ("Avalanche", 43114),
    ("Gnosis", 100),
    ("Linea", 59144),
    ("Scroll", 534352),
    ("Zora", 7777777),
]


def _eip55_checksum(addr_lower: str) -> str:
    """Apply EIP-55 checksum to a lowercase hex address (no 0x prefix)."""
    hash_hex = keccak256(addr_lower.encode("ascii")).hex()
    out = []
    # hash_hex is 64 chars, addr_lower is 40 chars; intentional non-strict zip
    for ch, hsh in zip(addr_lower, hash_hex):  # noqa: B905
        if ch in "0123456789":
            out.append(ch)
        elif int(hsh, 16) >= 8:
            out.append(ch.upper())
        else:
            out.append(ch)
    return "0x" + "".join(out)


class EVMValidator:
    chain = "ETH"
    formats = ["address-eip55", "address-no-checksum", "secp256k1-private-key"]

    def shape_match(self, candidate: Candidate) -> bool:
        s = candidate.normalized
        return bool(_ADDR_RE.match(s) or _PRIV_RE.match(s))

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        has_0x = s.startswith("0x") or s.startswith("0X")
        body = s[2:] if has_0x else s

        # Private key (64 hex = 32 bytes)
        if _PRIV_RE.match(s):
            try:
                key_bytes = bytes.fromhex(body)
            except ValueError:
                return None
            if key_bytes == b"\x00" * 32:  # invalid curve point
                return None
            return Match(
                chain="ETH",
                format="secp256k1-private-key",
                key_type="private-key",
                confidence=100,
                checksum_status="none",  # priv keys have no checksum
                network="mainnet",
                cross_chain_alternates=[(c, s) for c, _ in EVM_CHAINS[1:]],
                wallet_compatibility=wallets_for("ETH"),
                repairs_applied=candidate.repairs,
                notes=["PRIVATE KEY — handle with care", f"valid on {len(EVM_CHAINS)} EVM chains"],
            )

        # Address (40 hex = 20 bytes)
        if not _ADDR_RE.match(s):
            return None
        if len(body) != 40:
            return None

        # If all lower or all upper, no checksum applied
        if body.lower() == body or body.upper() == body:
            return Match(
                chain="ETH",
                format="address-no-checksum",
                key_type="address",
                confidence=50,
                checksum_status="none",
                network="mainnet",
                cross_chain_alternates=[(c, f"0x{body}") for c, _ in EVM_CHAINS[1:]],
                wallet_compatibility=wallets_for("ETH"),
                repairs_applied=candidate.repairs,
                notes=[f"same address works on {len(EVM_CHAINS)} EVM chains"],
            )

        # Mixed case — verify EIP-55
        expected = _eip55_checksum(body.lower())
        if expected == (f"0x{body}"):
            return Match(
                chain="ETH",
                format="address-eip55",
                key_type="address",
                confidence=100,
                checksum_status="valid",
                network="mainnet",
                cross_chain_alternates=[(c, expected) for c, _ in EVM_CHAINS[1:]],
                wallet_compatibility=wallets_for("ETH"),
                repairs_applied=candidate.repairs,
                notes=[f"same address works on {len(EVM_CHAINS)} EVM chains"],
            )
        else:
            # Checksum failed — could be a typo. Return low-confidence match.
            return Match(
                chain="ETH",
                format="address-eip55-failed",
                key_type="address",
                confidence=40,
                checksum_status="failed",
                network="mainnet",
                cross_chain_alternates=[],
                wallet_compatibility=wallets_for("ETH"),
                repairs_applied=candidate.repairs,
                notes=["EIP-55 checksum failed — likely typo", f"expected: {expected}"],
            )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        # EIP-55 fix is essentially free — produce a candidate with checksum applied
        s = candidate.normalized
        body = s[2:] if s.startswith(("0x", "0X")) else s
        if len(body) == 40:
            try:
                fixed = _eip55_checksum(body.lower())
                return [Candidate(
                    raw=candidate.raw,
                    normalized=fixed,
                    repairs=candidate.repairs + ["case:eip55"],
                    encoding=None, bytes_value=None,
                )]
            except Exception:
                pass
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return match.cross_chain_alternates
