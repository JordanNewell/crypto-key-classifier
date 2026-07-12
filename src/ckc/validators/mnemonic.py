"""Mnemonic validator: BIP-39 + Electrum detection + Levenshtein repair.

BIP-39 seeds: 12/15/18/21/24 words from the official 2048-word English wordlist.
Checksum = first ENT/32 bits of SHA-256(entropy), where ENT = words * 11 - checksum_bits.

Levenshtein repair: for each word not in wordlist, find wordlist entries within
distance <=2. If exactly one match, use it. If multiple, all become candidates.

Electrum detection: if BIP-39 checksum fails on a phrase where all words ARE in
the BIP-39 wordlist, flag as 'possibly Electrum' (Electrum 2.0+ uses HMAC-based
checksum, NOT BIP-39 compatible).
"""

from __future__ import annotations

import hashlib
import re
from importlib import resources

from ckc.models import Candidate, Match
from ckc.validators.base import levenshtein_distance


def _load_wordlist() -> tuple[list[str], dict[str, int]]:
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        words = [line.strip() for line in f if line.strip()]
    return words, {w: i for i, w in enumerate(words)}


_WORDLIST, _WORD_TO_INDEX = _load_wordlist()

# BIP-39 entropy / checksum / mnemonic-length table
_BIP39_PARAMS: dict[int, tuple[int, int]] = {
    12: (128, 4),
    15: (160, 5),
    18: (192, 6),
    21: (224, 7),
    24: (256, 8),
}

# Regex: N lowercase words separated by whitespace, N in {12, 15, 18, 21, 24}
_MNEMONIC_RE = re.compile(r"^[a-z]+(?:\s+[a-z]+){11,23}$")


def _words_to_entropy(words: list[str]) -> tuple[bytes, int] | None:
    """Convert wordlist indices to entropy + checksum bits.
    Returns (entropy_bytes, checksum_int) or None if any word isn't in wordlist.
    """
    if len(words) not in _BIP39_PARAMS:
        return None
    ent, cs = _BIP39_PARAMS[len(words)]
    bits = ""
    for word in words:
        idx = _WORD_TO_INDEX.get(word)
        if idx is None:
            return None
        bits += format(idx, "011b")
    entropy_bits = bits[:ent]
    checksum_bits = bits[ent:]
    entropy_bytes = int(entropy_bits, 2).to_bytes(ent // 8, "big")
    return entropy_bytes, int(checksum_bits, 2)


def _bip39_checksum_valid(entropy: bytes, cs_bits: int, expected: int) -> bool:
    """Verify BIP-39 checksum: first CS bits of SHA-256(entropy)."""
    if len(entropy) == 0:
        return False
    hash_int = int.from_bytes(hashlib.sha256(entropy).digest(), "big")
    actual = (hash_int >> (256 - cs_bits)) & ((1 << cs_bits) - 1)
    return actual == expected


class MnemonicValidator:
    chain = "BIP39"
    formats = ["mnemonic-12-word", "mnemonic-15-word", "mnemonic-18-word",
               "mnemonic-21-word", "mnemonic-24-word"]
    # Mnemonic derives keys for many chains — claim coverage for filtering
    chains_covered = {"BIP39", "BTC", "ETH", "SOL", "LTC", "DOGE", "ATOM"}

    def shape_match(self, candidate: Candidate) -> bool:
        s = candidate.normalized
        if not _MNEMONIC_RE.match(s):
            return False
        words = s.split()
        return len(words) in _BIP39_PARAMS

    def validate(self, candidate: Candidate) -> Match | None:
        s = candidate.normalized
        if not _MNEMONIC_RE.match(s):
            return None
        words = s.split()
        if len(words) not in _BIP39_PARAMS:
            return None

        result = _words_to_entropy(words)
        if result is None:
            # At least one word isn't in wordlist — Levenshtein in suggest_repairs handles it
            return None
        entropy, checksum_bits = result
        _, cs = _BIP39_PARAMS[len(words)]

        is_valid = _bip39_checksum_valid(entropy, cs, checksum_bits)
        fmt = f"mnemonic-{len(words)}-word"

        if is_valid:
            return Match(
                chain="BIP39",
                format=fmt,
                key_type="mnemonic",
                confidence=100,
                checksum_status="valid",
                network="mainnet",
                cross_chain_alternates=[],
                wallet_compatibility=[
                    "Ledger", "Trezor", "Bitcoin Core (import)", "Electrum",
                    "MetaMask", "Phantom", "Exodus",
                ],
                repairs_applied=candidate.repairs,
                notes=[
                    f"BIP-39 mnemonic ({len(words)} words = {len(words) * 11 - cs} bits entropy)",
                    "derives keys for BTC/LTC/DOGE/ETH/SOL/ATOM/etc. via BIP-32 paths",
                    "PRIVATE — handle with care (full wallet access)",
                ],
            )
        else:
            # Checksum failed. Could be Electrum (different checksum algo).
            return Match(
                chain="BIP39",
                format=fmt + "-checksum-failed",
                key_type="mnemonic",
                confidence=40,
                checksum_status="failed",
                network="mainnet",
                cross_chain_alternates=[],
                wallet_compatibility=[],
                repairs_applied=candidate.repairs,
                notes=[
                    "BIP-39 checksum FAILED",
                    "possibly Electrum seed (different checksum algorithm)",
                ],
            )

    def suggest_repairs(self, candidate: Candidate) -> list[Candidate]:
        """For each non-wordlist word, propose close matches via Levenshtein <=2."""
        s = candidate.normalized
        words = s.split()
        if len(words) not in _BIP39_PARAMS:
            return []

        # Find indices of words not in the wordlist
        bad_indices: list[int] = []
        for i, w in enumerate(words):
            if w not in _WORD_TO_INDEX:
                bad_indices.append(i)

        if not bad_indices:
            return []

        # Cap at 3 repairs
        bad_indices = bad_indices[:3]

        # For each bad word, find wordlist entries within distance 2
        repair_options: list[list[str]] = []
        for i in bad_indices:
            bad_word = words[i]
            candidates = []
            for w in _WORDLIST:
                if abs(len(w) - len(bad_word)) <= 2:
                    d = levenshtein_distance(bad_word, w)
                    if d <= 2:
                        candidates.append(w)
            if not candidates:
                return []
            repair_options.append(candidates)

        # Generate cartesian product (bounded at 8 total variants)
        result: list[Candidate] = []

        def _generate(idx: int, current_words: list[str]) -> None:
            if len(result) >= 8:
                return
            if idx == len(repair_options):
                repaired = " ".join(current_words)
                repairs = [
                    f"levenshtein:{words[bad_indices[j]]}->{current_words[bad_indices[j]]}"
                    for j in range(len(bad_indices))
                ]
                result.append(Candidate(
                    raw=candidate.raw,
                    normalized=repaired,
                    repairs=candidate.repairs + repairs,
                    encoding=None,
                    bytes_value=None,
                ))
                return
            bad_idx = bad_indices[idx]
            for new_word in repair_options[idx]:
                current_words[bad_idx] = new_word
                _generate(idx + 1, current_words)
                if len(result) >= 8:
                    return

        _generate(0, words[:])
        return result

    def cross_chain_encodings(self, match: Match) -> list[tuple[str, str]]:
        return []
