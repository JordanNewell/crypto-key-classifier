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


def preprocess(raw: str) -> list[Candidate]:
    """Generate Stage-1 normalized candidates from raw input.

    Returns a deduplicated list. The first candidate is always the
    "most normalized" form (whitespace stripped, lowercased for non-EIP-55).
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

    # Stage 1a: whitespace strip (most-normalized first)
    ws_stripped = _strip_all_whitespace(raw)
    add(ws_stripped, ["strip-ws"] if ws_stripped != raw else [])

    # Stage 1b: prefix drop
    for prefix in PREFIXES_TO_DROP:
        if ws_stripped.startswith(prefix):
            add(ws_stripped[len(prefix):], ["strip-ws", f"drop-prefix:{prefix}"])

    # Stage 1c: case variants. Only attribute "strip-ws" if whitespace was
    # actually stripped from the raw input — otherwise a pure case change gets
    # falsely downgraded in the pipeline's repair-confidence logic.
    case_repairs = ["strip-ws"] if ws_stripped != raw else []
    add(ws_stripped.lower(), [*case_repairs, "lowercase"])
    add(ws_stripped.upper(), [*case_repairs, "uppercase"])

    # Identity (no repairs) — added LAST so most-normalized is first
    add(raw, [])

    # Unicode NFC normalization as another variant
    nfc = unicodedata.normalize("NFC", ws_stripped)
    if nfc != ws_stripped:
        add(nfc, ["strip-ws", "unicode-nfc"])

    return candidates
