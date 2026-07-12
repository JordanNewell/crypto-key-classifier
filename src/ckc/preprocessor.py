"""Preprocessor: Stage 1 repairs (whitespace, prefix, case).

Generates a list of Candidate variants from a raw input string.
Stage 1 always runs; later stages (OCR, encoding, length) are in repairs.py.
"""

from __future__ import annotations

import re
import unicodedata

from ckc.models import Candidate

# Known format prefixes that may or may not be part of the canonical form
PREFIXES_TO_DROP: tuple[str, ...] = ("0x", "0X")

# Common unicode whitespace including zero-width chars (U+200B zero-width space,
# U+200C zero-width non-joiner, U+200D zero-width joiner, U+FEFF BOM, U+00A0 nbsp)
_WS_RE = re.compile(r"[\s​‌‍﻿\xa0]+")


def _strip_all_whitespace(s: str) -> str:
    """Strip ASCII + unicode whitespace including zero-width chars."""
    return _WS_RE.sub("", s)


def _normalize_whitespace(s: str) -> str:
    """Collapse runs of whitespace to single spaces, trim leading/trailing.

    Preserves internal word boundaries — critical for mnemonics where spaces
    between words are structural (the BIP-39 regex requires single-space
    separation). Use this instead of _strip_all_whitespace when internal
    whitespace is meaningful.
    """
    return _WS_RE.sub(" ", s).strip()


def preprocess(raw: str) -> list[Candidate]:
    """Generate Stage-1 normalized candidates from raw input.

    Returns a deduplicated list. The first candidate is always the
    "most normalized" form. Both a ws-normalized variant (preserves internal
    spaces, for mnemonics) and a ws-stripped variant (no internal spaces, for
    addresses/keys) are generated so downstream validators pick the right one.
    """
    if not raw:
        return []

    candidates: list[Candidate] = []
    seen: set[str] = set()

    def add(normalized: str, repairs: list[str]) -> None:
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(
                Candidate(
                    raw=raw,
                    normalized=normalized,
                    repairs=repairs,
                    encoding=None,
                    bytes_value=None,
                )
            )

    # Stage 1a-i: whitespace normalize (collapse runs to single spaces, trim).
    # Preserves internal word boundaries — needed for mnemonics.
    ws_normalized = _normalize_whitespace(raw)
    ws_stripped = _strip_all_whitespace(raw)

    # Repairs for the ws-normalized form. When ws_normalized == ws_stripped
    # (single-word input, only leading/trailing ws), "strip-ws" is the accurate
    # label. When they differ (multi-word input with preserved internal spaces),
    # "ws-normalize" is the accurate label.
    if ws_normalized == ws_stripped:
        ws_norm_repairs = ["strip-ws"] if ws_normalized != raw else []
    else:
        ws_norm_repairs = ["ws-normalize"] if ws_normalized != raw else []
    add(ws_normalized, ws_norm_repairs)

    # Stage 1a-ii: full whitespace strip (no internal spaces, for addresses/keys)
    strip_repairs = ["strip-ws"] if ws_stripped != raw else []
    if ws_stripped != ws_normalized:
        add(ws_stripped, strip_repairs)

    # Stage 1b: prefix drop on ws-stripped form
    for prefix in PREFIXES_TO_DROP:
        if ws_stripped.startswith(prefix):
            add(ws_stripped[len(prefix):], ["strip-ws", f"drop-prefix:{prefix}"])

    # Stage 1c: case variants — produce for BOTH ws-normalized and ws-stripped
    # forms so both mnemonic (needs internal spaces) and address/key (no
    # internal spaces) validators get a lowercase candidate.
    base_strip_repairs = strip_repairs
    base_norm_repairs = ws_norm_repairs
    add(ws_normalized.lower(), [*base_norm_repairs, "lowercase"])
    add(ws_stripped.lower(), [*base_strip_repairs, "lowercase"])
    add(ws_normalized.upper(), [*base_norm_repairs, "uppercase"])
    add(ws_stripped.upper(), [*base_strip_repairs, "uppercase"])

    # Identity (no repairs) — added LAST so most-normalized is first
    add(raw, [])

    # Unicode NFC normalization as another variant
    nfc = unicodedata.normalize("NFC", ws_stripped)
    if nfc != ws_stripped:
        add(nfc, ["strip-ws", "unicode-nfc"])

    return candidates
