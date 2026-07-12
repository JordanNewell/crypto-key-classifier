"""BTC-family validator: BTC, LTC, DOGE, BCH.

All four chains share base58check + WIF + bech32 machinery. The only
differences are P2PKH/P2SH version bytes. We decode once and dispatch on
the version byte to identify the chain, then cross-encode to all four.
"""

from __future__ import annotations

import re

from ckc.data.wallets import wallets_for
from ckc.models import Candidate, Match
from ckc.validators.base import (
    base58check_decode,
    base58check_encode,
    bech32_validate,
    convertbits,
)

# Version bytes per chain (P2PKH, P2SH)
# Source: https://en.bitcoin.it/wiki/List_of_address_prefixes
_VERSION_BYTES: dict[bytes, tuple[str, str]] = {
    b"\x00": ("BTC", "P2PKH"),
    b"\x05": ("BTC", "P2SH"),
    b"\x30": ("LTC", "P2PKH"),
    b"\x32": ("LTC", "P2SH"),
    b"\x1e": ("DOGE", "P2PKH"),
    b"\x16": ("DOGE", "P2SH"),
    # BCH uses the same addresses as BTC (cashaddr is separate, future work)
}

# For cross-chain encoding: map P2PKH version bytes for one-hop re-encoding
_P2PKH_VERSIONS: dict[str, bytes] = {
    "BTC": b"\x00",
    "LTC": b"\x30",
    "DOGE": b"\x1e",
    # BCH reuses BTC's addresses historically; cashaddr is separate
}
_P2SH_VERSIONS: dict[str, bytes] = {
    "BTC": b"\x05",
    "LTC": b"\x32",
    "DOGE": b"\x16",
}

# Charset shape matchers
_BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{25,62}$")
_BECH32_RE = re.compile(r"^bc1[02-9ac-hj-np-z]{6,87}$", re.IGNORECASE)


class BTCValidator:
    """Validator for BTC/LTC/DOGE/BCH address + key formats."""

    chain = "BTC_FAMILY"  # registry tag; per-match chain is more specific
    formats = ["P2PKH", "P2SH", "bech32-segwit-v0", "taproot-v1", "WIF"]

    def shape_match(self, candidate: Candidate) -> bool:
        s = candidate.normalized
        if _BASE58_RE.match(s):
            return True
        if _BECH32_RE.match(s):
            return True
        # WIF shape: 5x / Kx / Lx prefix, base58, ~51-52 chars
        if re.match(r"^[5KL][1-9A-HJ-NP-Za-km-z]{50,51}$", s):
            return True
        return False

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized

        # Try bech32 / bech32m first (cleaner dispatch)
        if s.lower().startswith("bc1"):
            return self._validate_bech32(candidate)

        # Try base58check (P2PKH / P2SH / WIF)
        payload = base58check_decode(s)
        if payload is None:
            return None

        # WIF private keys: prefix 0x80 (BTC), 0xB0 (LTC), 0x9E (DOGE)
        if payload[:1] in {b"\x80", b"\xb0", b"\x9e"}:
            return self._match_wif(candidate, payload)

        # P2PKH / P2SH: prefix byte tells us chain + format
        prefix = payload[:1]
        if prefix in _VERSION_BYTES:
            chain, fmt = _VERSION_BYTES[prefix]
            return self._match_address(candidate, chain, fmt, payload, s)

        return None

    def _validate_bech32(self, candidate: Candidate) -> Match | None:
        result = bech32_validate(candidate.normalized)
        if result is None:
            return None
        hrp, data, variant = result
        if hrp != "bc":
            return None
        # data[0] is the witness version byte
        if not data:
            return None
        witver = data[0]
        # bech32 for v0, bech32m for v1+
        expected_spec = "bech32m" if witver >= 1 else "bech32"
        if variant != expected_spec:
            return None

        # BIP-173 §"Decoding": witness program is data[1:] converted from 5-bit
        # to 8-bit groups. v0 programs MUST be 20 or 32 bytes; v1+ may be 2-40.
        program = convertbits(list(data[1:]), 5, 8, False)
        if program is None:
            return None
        if witver == 0 and len(program) not in (20, 32):
            return None
        if witver >= 1 and not (2 <= len(program) <= 40):
            return None

        fmt = "taproot-v1" if witver == 1 else f"bech32-segwit-v{witver}"
        return Match(
            chain="BTC",
            format=fmt,
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            wallet_compatibility=wallets_for("BTC"),
            repairs_applied=candidate.repairs,
            notes=[f"bech32 spec: {variant}"],
        )

    def _match_address(
        self, candidate: Candidate, chain: str, fmt: str, payload: bytes, original: str
    ) -> Match:
        return Match(
            chain=chain,
            format=fmt,
            key_type="address",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            cross_chain_alternates=self._cross_chain_for(chain, fmt, payload[1:]),
            wallet_compatibility=wallets_for(chain),
            repairs_applied=candidate.repairs,
            notes=[],
        )

    def _match_wif(self, candidate: Candidate, payload: bytes) -> Match:
        prefix = payload[:1]
        chain = {b"\x80": "BTC", b"\xb0": "LTC", b"\x9e": "DOGE"}.get(prefix, "BTC")
        # 0x01 suffix = compressed pubkey flag
        compressed = payload.endswith(b"\x01")
        return Match(
            chain=chain,
            format="WIF" + ("-compressed" if compressed else "-uncompressed"),
            key_type="private-key",
            confidence=100,
            checksum_status="valid",
            network="mainnet",
            wallet_compatibility=wallets_for(chain),
            repairs_applied=candidate.repairs,
            notes=["PRIVATE KEY — handle with care"],
        )

    def _cross_chain_for(self, chain: str, fmt: str, hash160: bytes) -> list[tuple[str, str]]:
        """For a decoded 20-byte hash160, enumerate cross-chain encodings."""
        out: list[tuple[str, str]] = []

        if fmt == "P2PKH":
            for alt_chain, version in _P2PKH_VERSIONS.items():
                if alt_chain == chain:
                    continue
                out.append((alt_chain, base58check_encode(version + hash160)))
        elif fmt == "P2SH":
            for alt_chain, version in _P2SH_VERSIONS.items():
                if alt_chain == chain:
                    continue
                out.append((alt_chain, base58check_encode(version + hash160)))
        return out

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        # BTC validator relies on generic repair layer
        return []

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return match.cross_chain_alternates
