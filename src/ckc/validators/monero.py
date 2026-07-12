"""Monero (XMR) validator.

Monero address format:
  network_byte(1) + spend_pubkey(32) + view_pubkey(32) + checksum(4)
  = 69 bytes total

Checksum = first 4 bytes of Keccak-256(network + spend + view)
         = first 4 bytes of Keccak-256(first 65 bytes)

Encoding: Monero BLOCK-ENCODED base58 (8-byte blocks → 11 chars each).
69 bytes = 8 full blocks (64 bytes) + 5-byte remainder → 88 + 7 = 95 chars.

Network bytes:
  0x12 = mainnet (standard addresses start with '4', subaddresses '8')
  0x18 = stagenet
  0x35 = testnet
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import keccak256, monero_base58_decode, monero_base58_encode

# Monero mainnet addresses are exactly 95 chars (69 bytes encoded)
# Could be 95 (mainnet/stagenet/testnet standard) or longer for payment IDs (integrated)
_MONERO_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{95}$")

_NETWORK_BYTES: dict[int, tuple[str, str]] = {
    0x12: ("XMR", "mainnet"),
    0x18: ("XMR", "stagenet"),
    0x35: ("XMR", "testnet"),
}


def monero_encode_address(full_payload_69_bytes: bytes) -> str:
    """Encode a 69-byte Monero address payload as block-encoded base58."""
    if len(full_payload_69_bytes) != 69:
        raise ValueError(f"expected 69 bytes, got {len(full_payload_69_bytes)}")
    return monero_base58_encode(full_payload_69_bytes)


class MoneroValidator:
    chain = "XMR"
    formats = ["address"]

    def shape_match(self, candidate: Candidate) -> bool:
        return bool(_MONERO_RE.match(candidate.normalized))

    def _decode(self, s: str) -> bytes | None:
        """Decode + verify checksum. Returns 69-byte payload or None."""
        try:
            raw = monero_base58_decode(s)
        except Exception:
            return None
        if len(raw) != 69:
            return None
        payload, checksum = raw[:65], raw[65:]
        expected = keccak256(payload)[:4]
        if checksum != expected:
            return None
        return raw

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _MONERO_RE.match(s):
            return None
        decoded = self._decode(s)
        if decoded is None:
            return None
        network_byte = decoded[0]
        if network_byte not in _NETWORK_BYTES:
            return None
        chain, network = _NETWORK_BYTES[network_byte]
        return Match(
            chain=chain,
            format="address",
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network=network,
            cross_chain_alternates=[],
            wallet_compatibility=wallets_for(chain),
            repairs_applied=candidate.repairs,
            notes=[
                f"network byte: 0x{network_byte:02x}",
                "block-encoded base58 (8B → 11 char blocks)",
            ],
        )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
