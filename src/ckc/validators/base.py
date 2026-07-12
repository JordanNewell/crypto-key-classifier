"""Validator protocol + shared crypto helpers.

Each chain validator subclasses Validator and implements shape_match,
validate, suggest_repairs, and (optionally) cross_chain_encodings.

Bech32/bech32m (BIP-173 + BIP-350) is embedded directly from the official
reference implementation to avoid external package API mismatches.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import base58
from Crypto.Hash import keccak

from ckc.models import Candidate, Match


class Validator(Protocol):
    """Protocol every validator implements.

    Concrete validators are discovered by validators/__init__.py via pkgutil.
    """

    chain: str
    formats: list[str]

    def shape_match(self, candidate: Candidate) -> bool:
        """Cheap check: right length, charset, prefix? No checksum yet."""
        ...

    def validate(self, candidate: Candidate) -> Match | None:
        """Strict validation: checksum, network byte, etc. Returns None if rejected."""
        ...

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        """Format-specific repair candidates (return [] to defer to generic layer)."""
        ...

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        """For shared-key families: enumerate alternate chain encodings."""
        ...


# --- Shared crypto helpers ---


def keccak256(data: bytes) -> bytes:
    """Keccak-256 hash (NOT SHA3-256 — different padding)."""
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def double_sha256(data: bytes) -> bytes:
    return sha256(sha256(data))


def base58check_encode(payload: bytes) -> str:
    """Encode payload with double-SHA256 checksum (4 bytes)."""
    checksum = double_sha256(payload)[:4]
    return base58.b58encode(payload + checksum).decode("ascii")


def base58check_decode(s: str) -> bytes | None:
    """Decode base58check-encoded string. Returns payload WITHOUT checksum,
    or None if checksum fails."""
    try:
        full = base58.b58decode(s)
    except Exception:
        return None
    if len(full) < 5:
        return None
    payload, checksum = full[:-4], full[-4:]
    if double_sha256(payload)[:4] != checksum:
        return None
    return payload


# --- Bech32 / Bech32m (BIP-173 + BIP-350) ---
# Adapted from official reference: https://github.com/sipa/bech32/blob/master/ref/python/segwit_addr.py

BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32M_CONST = 0x2bc830a3


def _bech32_polymod(values: list[int]) -> int:
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_verify_checksum(hrp: str, data: list[int]) -> str | None:
    """Return 'bech32', 'bech32m', or None if checksum invalid."""
    const = _bech32_polymod(_bech32_hrp_expand(hrp) + data)
    if const == 1:
        return "bech32"
    if const == BECH32M_CONST:
        return "bech32m"
    return None


def _bech32_create_checksum(hrp: str, data: list[int], spec: str) -> list[int]:
    const = 1 if spec == "bech32" else BECH32M_CONST
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ const
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def bech32_encode(hrp: str, data: list[int], spec: str = "bech32") -> str:
    """Encode hrp + 5-bit data values with bech32 or bech32m checksum."""
    combined = data + _bech32_create_checksum(hrp, data, spec)
    return hrp + "1" + "".join([BECH32_CHARSET[d] for d in combined])


def bech32_decode(bech: str) -> tuple[str, list[int], str] | None:
    """Decode a bech32(bech32m) string. Returns (hrp, data, spec) or None."""
    if any(ord(x) < 33 or ord(x) > 126 for x in bech):
        return None
    if bech.lower() != bech and bech.upper() != bech:
        return None
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
        return None
    if not all(x in BECH32_CHARSET for x in bech[pos + 1:]):
        return None
    hrp = bech[:pos]
    data = [BECH32_CHARSET.find(x) for x in bech[pos + 1:]]
    spec = _bech32_verify_checksum(hrp, data)
    if spec is None:
        return None
    return (hrp, data[:-6], spec)


def convertbits(data: list[int], frombits: int, tobits: int, pad: bool = True) -> list[int] | None:
    """Convert between bit group sizes (e.g. 8-bit bytes ↔ 5-bit bech32 groups)."""
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def bech32_validate(s: str) -> tuple[str, bytes, str] | None:
    """Validate bech32/bech32m string. Returns (hrp, 5-bit-data, variant) or None.

    variant is 'bech32' or 'bech32m' depending on BIP-173 vs BIP-350.
    Note: data is returned as the raw 5-bit values (list[int] converted to bytes).
    Callers wanting 8-bit bytes must call convertbits() themselves.
    """
    result = bech32_decode(s)
    if result is None:
        return None
    hrp, data, spec = result
    return (hrp, bytes(data), spec)


# =====================================================================
# Long-tail chain helpers (Plan 2)
# =====================================================================


def crc16_xmodem(data: bytes) -> int:
    """CRC16-XMODEM (used by Stellar, TON). Polynomial 0x1021, init 0x0000."""
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def blake2b(data: bytes, digest_size: int = 32) -> bytes:
    """BLAKE2b hash with configurable digest size."""
    import hashlib
    return hashlib.blake2b(data, digest_size=digest_size).digest()


def sha512_256(data: bytes) -> bytes:
    """SHA-512/256 (NIST variant, used by Algorand). NOT truncated SHA-512."""
    import hashlib
    return hashlib.new("sha512_256", data).digest()


# --- Monero block-encoded base58 ---
# Monero encodes 8-byte blocks → 11 chars each. The last block carries
# any remainder bytes (1-7), producing 2-10 chars. This is DIFFERENT from
# Bitcoin base58check which encodes the whole payload as one integer.
#
# Mapping (remainder_bytes → output_chars):
#   0 → 0, 1 → 2, 2 → 3, 3 → 5, 4 → 6, 5 → 7, 6 → 9, 7 → 10, 8 → 11

_MONERO_BLOCK_SIZES: list[tuple[int, int]] = [
    (0, 0), (2, 1), (3, 2), (5, 3), (6, 4), (7, 5), (9, 6), (10, 7), (11, 8),
]

# Indexed by remainder chars → (remainder_bytes_in_block, encoded_size)
# Actually, we need: given how many FULL bytes remain, what encoded size?
_MONERO_ENCODE_TABLE: dict[int, tuple[int, int]] = {
    # remainder_bytes_in_block → (encoded_chars, bytes_consumed)
    8: (11, 8),
    7: (10, 7),
    6: (9, 6),
    5: (7, 5),
    4: (6, 4),
    3: (5, 3),
    2: (3, 2),
    1: (2, 1),
    0: (0, 0),
}

_MONERO_DECODE_TABLE: dict[int, tuple[int, int]] = {
    # encoded_chars → (bytes_produced, chars_consumed)
    11: (8, 11),
    10: (7, 10),
    9: (6, 9),
    7: (5, 7),
    6: (4, 6),
    5: (3, 5),
    3: (2, 3),
    2: (1, 2),
    0: (0, 0),
}

_MONERO_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_MONERO_BASE58_INDEX = {c: i for i, c in enumerate(_MONERO_BASE58_ALPHABET)}


def _monero_encode_block(data: bytes, from_index: int) -> tuple[str, int]:
    """Encode a single Monero base58 block. Returns (encoded_chars, next_index)."""
    remaining = len(data) - from_index
    if remaining >= 8:
        block_size = 8
        encoded_size = 11
    else:
        encoded_size, block_size = _MONERO_ENCODE_TABLE[remaining]

    block = data[from_index:from_index + block_size]
    num = int.from_bytes(block, "big") if block else 0
    chars = []
    for _ in range(encoded_size):
        num, rem = divmod(num, 58)
        chars.append(_MONERO_BASE58_ALPHABET[rem])
    return "".join(reversed(chars)), from_index + block_size


def monero_base58_encode(data: bytes) -> str:
    """Encode bytes using Monero's block-encoded base58 (8-byte → 11-char blocks)."""
    result = []
    i = 0
    while i < len(data):
        encoded, i = _monero_encode_block(data, i)
        result.append(encoded)
    return "".join(result)


def monero_base58_decode(s: str) -> bytes:
    """Decode Monero's block-encoded base58."""
    full_blocks = len(s) // 11
    remainder_chars = len(s) % 11

    result = b""
    pos = 0
    for _ in range(full_blocks):
        block_str = s[pos:pos + 11]
        pos += 11
        num = 0
        for ch in block_str:
            if ch not in _MONERO_BASE58_INDEX:
                raise ValueError(f"invalid char {ch!r}")
            num = num * 58 + _MONERO_BASE58_INDEX[ch]
        result += num.to_bytes(8, "big")

    if remainder_chars:
        if remainder_chars not in _MONERO_DECODE_TABLE:
            raise ValueError(f"invalid remainder char count {remainder_chars}")
        remainder_bytes, _ = _MONERO_DECODE_TABLE[remainder_chars]
        block_str = s[pos:pos + remainder_chars]
        num = 0
        for ch in block_str:
            if ch not in _MONERO_BASE58_INDEX:
                raise ValueError(f"invalid char {ch!r}")
            num = num * 58 + _MONERO_BASE58_INDEX[ch]
        result += num.to_bytes(remainder_bytes, "big")

    return result
