"""Mutation functions: take a valid key string, return a corrupted variant.

Each mutation is small and well-defined so we can measure recovery rates
per mutation type.
"""

from __future__ import annotations

import random

from ckc.repairs import OCR_MAP


def whitespace_pollution(s: str) -> str:
    """Add spaces/newlines/tabs around the string."""
    n_lead = random.randint(1, 5)
    n_trail = random.randint(1, 5)
    ws_chars = [" ", "\n", "\t", "\xa0", "​"]  # last is zero-width space
    lead = "".join(random.choice(ws_chars) for _ in range(n_lead))
    trail = "".join(random.choice(ws_chars) for _ in range(n_trail))
    return lead + s + trail


def case_flip(s: str) -> str:
    """Flip case of one alphabetic character."""
    alpha_indices = [i for i, c in enumerate(s) if c.isalpha()]
    if not alpha_indices:
        return s
    idx = random.choice(alpha_indices)
    ch = s[idx]
    flipped = ch.lower() if ch.isupper() else ch.upper()
    return s[:idx] + flipped + s[idx + 1:]


def char_substitute(s: str) -> str:
    """Replace one char with another from a plausible charset."""
    if len(s) < 2:
        return s
    idx = random.randint(0, len(s) - 1)
    new_char = random.choice([c for i, c in enumerate(s) if i != idx])
    return s[:idx] + new_char + s[idx + 1:]


def char_delete(s: str) -> str:
    """Remove one character."""
    if len(s) < 2:
        return s
    idx = random.randint(0, len(s) - 1)
    return s[:idx] + s[idx + 1:]


def char_insert(s: str) -> str:
    """Insert one random char at a random position."""
    if not s:
        return s
    idx = random.randint(0, len(s))
    new_char = random.choice(s)
    return s[:idx] + new_char + s[idx:]


def char_swap_adjacent(s: str) -> str:
    """Swap two adjacent characters."""
    if len(s) < 2:
        return s
    idx = random.randint(0, len(s) - 2)
    return s[:idx] + s[idx + 1] + s[idx] + s[idx + 2:]


def ocr_substitute(s: str) -> str:
    """Apply one OCR confusable substitution (O→0, l→1, S→5, etc.)."""
    candidates = [(i, ch, OCR_MAP[ch]) for i, ch in enumerate(s) if ch in OCR_MAP]
    if not candidates:
        return s
    idx, old, new = random.choice(candidates)
    return s[:idx] + new + s[idx + 1:]


ALL_MUTATIONS = [
    whitespace_pollution,
    case_flip,
    char_substitute,
    char_delete,
    char_insert,
    char_swap_adjacent,
    ocr_substitute,
]
