"""Stage 2-4 repair primitives.

Each function takes a Candidate (or string + context) and returns *additional*
candidates. These are composable; the pipeline decides which stages to invoke.

Stages:
  2: OCR confusables (one char at a time)
  3: Encoding round-trips (hex/base58/base64)
  4: Length repair (±2 chars, bounded)

Cap: MAX_CANDIDATES total per input across all stages.
"""

from __future__ import annotations

import base64
import binascii

import base58

from ckc.models import Candidate

MAX_CANDIDATES = 50

# Visual confusables — common OCR / handwritten substitutions
# Map of "looks-like" → "actually-is". Bidirectional in practice.
OCR_MAP: dict[str, str] = {
    "O": "0",
    "o": "0",
    "I": "1",
    "l": "1",
    "|": "1",
    "S": "5",
    "s": "5",
    "B": "8",
    "Z": "2",
    "z": "2",
    "G": "6",
    "D": "0",  # partial — only in some fonts
    "q": "9",
}


def ocr_substitutions(text: str) -> list[Candidate]:
    """Stage 2: produce one variant per confusable char, replacing just that char."""
    candidates: list[Candidate] = []
    for i, ch in enumerate(text):
        if ch in OCR_MAP:
            replacement = OCR_MAP[ch]
            new = text[:i] + replacement + text[i + 1:]
            cand = Candidate(
                raw=text,
                normalized=new,
                repairs=[f"ocr:{ch}→{replacement}@{i}"],
                encoding=None,
                bytes_value=None,
            )
            candidates.append(cand)
    return candidates


def encoding_variants(text: str) -> list[Candidate]:
    """Stage 3: try decoding text as hex/base58/base64, attach bytes_value.

    The validator can use bytes_value for downstream checks (length, prefix byte).
    """
    candidates: list[Candidate] = []

    # Hex
    try:
        b = bytes.fromhex(text)
        candidates.append(
            Candidate(
                raw=text, normalized=text, repairs=["decode:hex"],
                encoding="hex", bytes_value=b,
            )
        )
    except ValueError:
        pass

    # Base58 (Bitcoin alphabet)
    try:
        b = base58.b58decode(text)
        candidates.append(
            Candidate(
                raw=text, normalized=text, repairs=["decode:base58"],
                encoding="base58", bytes_value=b,
            )
        )
    except Exception:
        pass

    # Base64 (standard)
    try:
        b = base64.b64decode(text, validate=True)
        candidates.append(
            Candidate(
                raw=text, normalized=text, repairs=["decode:base64"],
                encoding="base64", bytes_value=b,
            )
        )
    except (binascii.Error, ValueError):
        pass

    return candidates


def length_repairs(text: str, target_lengths: set[int]) -> list[Candidate]:
    """Stage 4: produce variants with chars inserted/deleted to hit target lengths.

    Insertion: at each position, insert a placeholder ('?' or actual char from a
    small candidate set if provided). The validator is responsible for trying
    checksums against the candidate variants.

    For deletion: at each position, remove that one char.

    Bounded to ±2 chars from current length to avoid combinatorial blowup.
    """
    candidates: list[Candidate] = []
    current = len(text)

    for target in target_lengths:
        delta = target - current
        if abs(delta) > 2:
            continue

        if delta > 0:
            # Insertions: at each position, insert N placeholder chars
            for pos in range(current + 1):
                for _ in range(delta):
                    # Placeholder; validator handles char substitution
                    new = text[:pos] + "?" + text[pos:]
                    candidates.append(
                        Candidate(
                            raw=text, normalized=new,
                            repairs=[f"len-repair:insert@{pos}"],
                            encoding=None, bytes_value=None,
                        )
                    )
                    break  # one insertion per position per target
        elif delta < 0:
            # Deletions: at each position, remove that char
            for pos in range(current):
                new = text[:pos] + text[pos + 1:]
                candidates.append(
                    Candidate(
                        raw=text, normalized=new,
                        repairs=[f"len-repair:delete@{pos}"],
                        encoding=None, bytes_value=None,
                    )
                )

    return candidates
