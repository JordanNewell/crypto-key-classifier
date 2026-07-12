from ckc.models import Match
from ckc.reporter import mask_key, render_json, render_rich, render_terse


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
