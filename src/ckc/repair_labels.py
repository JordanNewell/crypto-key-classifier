"""Human-readable repair-trace entries.

The pipeline records each applied repair as a string in
``Candidate.repairs`` / ``Match.repairs_applied``. Historically these were terse
slugs (``"strip-ws"``, ``"decode:hex"``, ...) which are meaningless to humans
without code context but are load-bearing identifiers in
:func:`ckc.pipeline._adjust_confidence_for_repairs`.

This module defines the canonical format:

    "<slug> — <human-readable description>"

* The slug half is what the pipeline's tier-matching logic keys off.
* The description half is what renders in ``--explain`` output and the web demo.

Emitters should always go through :func:`repair_entry` (or the per-kind helpers
below) so the separator stays consistent. Consumers that need the slug half
should call :func:`slug_of`; consumers that need the human half should call
:func:`description_of`.
"""

from __future__ import annotations

# Separator between programmatic slug and human description. An em-dash flanked
# by spaces is unlikely to appear inside either half and renders cleanly in both
# the terminal and the web demo.
_SEP = " — "


def repair_entry(slug: str, description: str) -> str:
    """Build a ``"<slug> — <description>"`` entry.

    Args:
        slug: short programmatic identifier (e.g. ``"strip-ws"``, ``"decode:hex"``).
        description: human-readable sentence fragment (no leading verb needed if
            the slug already conveys action, but a leading verb reads best).

    Returns:
        Combined entry. If ``description`` is empty, returns the slug alone
        (back-compat for any emitter that hasn't been migrated).
    """
    if not description:
        return slug
    return f"{slug}{_SEP}{description}"


def slug_of(entry: str) -> str:
    """Extract the slug half of a repair entry.

    For un-migrated entries (no separator) returns the whole string, so this is
    safe to call on any historical data.
    """
    if _SEP in entry:
        return entry.split(_SEP, 1)[0]
    return entry


def description_of(entry: str) -> str:
    """Extract the human-readable half of a repair entry, or the slug if absent."""
    if _SEP in entry:
        return entry.split(_SEP, 1)[1]
    return entry


# --- Per-kind builders -------------------------------------------------------
# Centralised so the wording stays consistent across emitters and the counts
# (chars stripped, bytes decoded) are computed at the call site that knows them.


def strip_ws(stripped_chars: int) -> str:
    """Whitespace strip. ``stripped_chars`` is total whitespace removed."""
    if stripped_chars > 0:
        return repair_entry("strip-ws", f"Stripped {stripped_chars} chars of whitespace")
    return repair_entry("strip-ws", "Stripped leading/trailing whitespace")


def ws_normalize(leading: int, internal_runs: int) -> str:
    """Whitespace normalisation that preserves internal word boundaries."""
    parts: list[str] = []
    if leading > 0:
        parts.append(f"{leading} chars of leading/trailing whitespace")
    if internal_runs > 0:
        parts.append(f"collapsed {internal_runs} internal whitespace run(s)")
    desc = "; ".join(parts) if parts else "Normalised whitespace"
    return repair_entry("ws-normalize", f"Normalised whitespace ({desc})")


def drop_prefix(prefix: str) -> str:
    return repair_entry(f"drop-prefix:{prefix}", f"Dropped '{prefix}' prefix")


def lowercase() -> str:
    return repair_entry("lowercase", "Lowercased the input")


def uppercase() -> str:
    return repair_entry("uppercase", "Uppercased the input")


def unicode_nfc() -> str:
    return repair_entry(
        "unicode-nfc", "Normalised to Unicode NFC (canonical composition)"
    )


def case_eip55() -> str:
    return repair_entry("case:eip55", "Applied EIP-55 mixed-case checksum")


def ocr_sub(ch: str, replacement: str, position: int) -> str:
    return repair_entry(
        f"ocr:{ch}→{replacement}@{position}",
        f"Swapped confusable '{ch}' → '{replacement}' at position {position}",
    )


def decode_hex(num_bytes: int) -> str:
    return repair_entry("decode:hex", f"Decoded hex to bytes ({num_bytes} bytes)")


def decode_base58(num_bytes: int) -> str:
    return repair_entry("decode:base58", f"Decoded base58 to bytes ({num_bytes} bytes)")


def decode_base64(num_bytes: int) -> str:
    return repair_entry("decode:base64", f"Decoded base64 to bytes ({num_bytes} bytes)")


def len_repair_insert(position: int) -> str:
    return repair_entry(
        f"len-repair:insert@{position}",
        f"Inserted placeholder char at position {position} (length repair)",
    )


def len_repair_delete(position: int) -> str:
    return repair_entry(
        f"len-repair:delete@{position}",
        f"Deleted char at position {position} (length repair)",
    )


def levenshtein(original: str, replacement: str) -> str:
    return repair_entry(
        f"levenshtein:{original}->{replacement}",
        f"Corrected mnemonic word '{original}' → '{replacement}' (edit distance ≤ 2)",
    )
