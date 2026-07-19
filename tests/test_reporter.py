from ckc.models import Match
from ckc.reporter import (
    mask_key,
    render_json,
    render_json_array,
    render_rich,
    render_terse,
    truncate_for_display,
)


def _match(chain="BTC", confidence=100, key_type="address", checksum="valid"):
    return Match(
        chain=chain, format="P2PKH", key_type=key_type,
        confidence=confidence, checksum_status=checksum,
        network="mainnet", cross_chain_alternates=[("LTC", "Labc")],
        wallet_compatibility=["Electrum"], repairs_applied=[], notes=[],
    )


def test_render_rich_includes_chain():
    out = render_rich("input", [_match()])
    assert "BTC" in out
    assert "100%" in out
    assert "Electrum" in out


def test_render_terse_one_line():
    out = render_terse("input", [_match()])
    assert "input" in out
    assert "BTC/P2PKH" in out
    assert "100%" in out
    # Should be one line per input
    assert out.count("\n") <= 1


def test_render_json_parses():
    import json
    out = render_json("input", [_match()])
    parsed = json.loads(out)
    assert parsed["input"] == "input"
    assert parsed["matches"][0]["chain"] == "BTC"


def test_mask_key_for_private_key():
    masked = mask_key("5Kb8cY8s9MwLq4m3F7o2Vd1pZaXyHgNvBc", key_type="private-key")
    # Should show first 4 + last 4 chars
    assert masked.startswith("5Kb8")
    assert masked.endswith("NvBc")
    assert "..." in masked


def test_mask_key_off_for_address():
    addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert mask_key(addr, key_type="address") == addr


def test_private_key_alternates_are_masked():
    """Regression for Issue #1: cross-chain alternates for private keys must
    be masked in default rich output — the raw private key string must never
    appear verbatim."""
    raw_pk = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
    m = Match(
        chain="ETH",
        format="secp256k1-private-key",
        key_type="private-key",
        confidence=100,
        checksum_status="none",
        network="mainnet",
        cross_chain_alternates=[("Polygon", raw_pk), ("Base", raw_pk)],
        wallet_compatibility=[],
        repairs_applied=[],
        notes=[],
    )
    out = render_rich(raw_pk, [m], mask_private_keys=True)
    # The raw key must NOT appear anywhere in the rendered output.
    assert raw_pk not in out
    # Masked form (mask_key returns s[:4]...s[-4:]) should be present instead.
    assert "0x4c...2318" in out


def test_private_key_alternates_are_masked_json():
    """Regression for Issue #1: JSON output must also mask private-key
    cross-chain alternates."""
    import json

    raw_pk = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
    m = Match(
        chain="ETH",
        format="secp256k1-private-key",
        key_type="private-key",
        confidence=100,
        checksum_status="none",
        network="mainnet",
        cross_chain_alternates=[("Polygon", raw_pk)],
        wallet_compatibility=[],
        repairs_applied=[],
        notes=[],
    )
    out = render_json(raw_pk, [m], mask_private_keys=True)
    assert raw_pk not in out
    parsed = json.loads(out)
    # alternates tuple round-trips as a list in JSON
    alt_value = parsed["matches"][0]["cross_chain_alternates"][0][1]
    assert raw_pk not in alt_value


def test_render_json_array_is_single_document():
    """Regression: batch --json must be one JSON array (not concatenated
    objects). Stranger test caught `jq '.[]'` failing because output was
    multiple documents."""
    import json

    m = _match()
    out = render_json_array([("input-a", [m]), ("input-b", [m])])
    parsed = json.loads(out)  # must not raise
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0]["input"] == "input-a"
    assert parsed[1]["input"] == "input-b"


def test_render_json_array_empty():
    import json

    out = render_json_array([])
    assert json.loads(out) == []


def test_truncate_for_display_short_input_unchanged():
    assert truncate_for_display("short") == "short"
    assert truncate_for_display("x" * 80) == "x" * 80  # boundary


def test_truncate_for_display_long_input_truncated():
    """Regression: paste-corrupted input (valid key + thousands of trailing
    chars) used to dump the entire blob into the INPUT: echo line. Echo must
    cap at ~80 chars with prefix + suffix preserved."""
    long_input = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" + "X" * 4000
    out = truncate_for_display(long_input)
    assert len(out) <= 80
    assert out.startswith("1A1zP1eP5Q")
    assert out.endswith("XXX")
    assert "..." in out


def test_render_rich_truncates_long_input():
    """End-to-end: render_rich must not emit the full 4000-char input."""
    long_input = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" + "X" * 4000
    out = render_rich(long_input, [], mask_private_keys=True)
    input_line = next(line for line in out.splitlines() if line.startswith("INPUT:"))
    # Echo line should be ~80 chars max, not 4000+
    assert len(input_line) < 120
    assert "X" * 100 not in out
