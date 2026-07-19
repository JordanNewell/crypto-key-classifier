"""Output rendering: rich / terse / json.

All renderers take (input_string, list[Match]) and return a string.
Masking is applied at this layer so private keys never leak in default mode.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from ckc.models import Match

# Cap for the INPUT: echo line. Paste-corrupted inputs (valid key + thousands
# of trailing chars) otherwise dump the entire blob into the terminal.
_ECHO_MAX = 80


def mask_key(s: str, key_type: str, mask_private_keys: bool = True) -> str:
    """Mask private keys by default. Addresses are public — never masked."""
    # Both "private-key" and "mnemonic" are sensitive and should be masked
    if not mask_private_keys or key_type not in {"private-key", "mnemonic"}:
        return s
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}...{s[-4:]}"


def truncate_for_display(s: str, max_len: int = _ECHO_MAX) -> str:
    """Truncate long inputs for the INPUT: echo line.

    Keeps the prefix and suffix visible so the user can still recognize the
    key. Applied AFTER masking, so masked private keys (already short) are
    unaffected.
    """
    if len(s) <= max_len:
        return s
    keep = max_len - 3
    head = keep * 2 // 3
    tail = keep - head
    return f"{s[:head]}...{s[-tail:]}"


def render_rich(
    input_str: str,
    matches: list[Match],
    mask_private_keys: bool = True,
    show_wallets: bool = True,
    show_cross_chain: bool = True,
    explain: bool = True,
) -> str:
    """Rich multi-line output for single-input mode."""
    lines: list[str] = []
    masked_input = mask_key(input_str, _infer_key_type(matches), mask_private_keys)
    lines.append(f"INPUT: {truncate_for_display(masked_input)}")
    lines.append("")

    if not matches:
        lines.append("No matches found.")
        return "\n".join(lines)

    for i, m in enumerate(matches, 1):
        prefix = "✓" if i == 1 else " "
        lines.append(f"{prefix} MATCH ({m.confidence}%): {m.chain} {m.format}")
        lines.append(f"    Chain:        {m.chain}")
        lines.append(f"    Format:       {m.format}")
        lines.append(f"    Key type:     {m.key_type}")
        lines.append(f"    Checksum:     {m.checksum_status}")
        if m.network:
            lines.append(f"    Network:      {m.network}")
        if show_wallets and m.wallet_compatibility:
            lines.append(f"    Wallets:      {', '.join(m.wallet_compatibility)}")
        if show_cross_chain and m.cross_chain_alternates:
            lines.append("    Cross-chain:  same key as →")
            for chain, addr in m.cross_chain_alternates[:10]:
                # Defense-in-depth: mask private-key alternates even if an
                # upstream validator accidentally emitted raw key material.
                # When mask_private_keys=False (--no-mask), mask_key is a no-op
                # for addresses and returns the value unchanged for PKs only if
                # the flag is False — preserving the explicit opt-in escape hatch.
                display = mask_key(addr, m.key_type, mask_private_keys)
                lines.append(f"      • {chain:6}  {display}")
            if len(m.cross_chain_alternates) > 10:
                lines.append(f"      • [+{len(m.cross_chain_alternates) - 10} more]")
        if explain and m.repairs_applied:
            lines.append(f"    Repairs:      {', '.join(m.repairs_applied)}")
        if m.notes:
            for note in m.notes:
                lines.append(f"    Note:         {note}")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_terse(
    input_str: str,
    matches: list[Match],
    mask_private_keys: bool = True,
) -> str:
    """One-line-per-input output for batch mode."""
    masked_input = mask_key(input_str, _infer_key_type(matches), mask_private_keys)
    echoed = truncate_for_display(masked_input)
    if not matches:
        return f"{echoed:30.30}  → NO MATCH"
    top = matches[0]
    return (
        f"{echoed:30.30}  → {top.chain}/{top.format} "
        f"({top.confidence}%, checksum {top.checksum_status})"
    )


def render_json(
    input_str: str,
    matches: list[Match],
    mask_private_keys: bool = True,
) -> str:
    """Single-input JSON (one object). Kept as a public helper."""
    return json.dumps(
        _json_payload(input_str, matches, mask_private_keys), indent=2
    )


def render_json_array(
    items: list[tuple[str, list[Match]]],
    mask_private_keys: bool = True,
) -> str:
    """Batch JSON: a single array wrapping one payload per input.

    Output is a JSON array so `jq '.[] | .best_guess'` works as documented,
    for both single-input and batch invocations.
    """
    return json.dumps(
        [_json_payload(raw, matches, mask_private_keys) for raw, matches in items],
        indent=2,
    )


def _json_payload(
    input_str: str,
    matches: list[Match],
    mask_private_keys: bool = True,
) -> dict[str, object]:
    masked_input = mask_key(input_str, _infer_key_type(matches), mask_private_keys)
    return {
        "input": masked_input,
        "best_guess": matches[0].chain if matches else None,
        "matches": [_match_to_dict(m, mask_private_keys) for m in matches],
    }


def _match_to_dict(m: Match, mask_private_keys: bool = True) -> dict[str, object]:
    d = asdict(m)
    if (
        mask_private_keys
        and m.key_type in {"private-key", "mnemonic"}
        and d.get("cross_chain_alternates")
    ):
        d["cross_chain_alternates"] = [
            (chain, mask_key(addr, m.key_type, True))
            for chain, addr in d["cross_chain_alternates"]
        ]
    return d


def _infer_key_type(matches: list[Match]) -> str:
    """Infer key type from matches for masking decisions."""
    if matches and matches[0].key_type in {"private-key", "mnemonic"}:
        return matches[0].key_type
    return "address"
