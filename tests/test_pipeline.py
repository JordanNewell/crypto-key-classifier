from ckc.pipeline import Config, classify


def test_clean_btc_address():
    results = classify("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert len(results) >= 1
    top = results[0]
    assert top.chain == "BTC"
    assert top.confidence == 100


def test_strip_whitespace_then_classify():
    results = classify("  1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa  \n")
    top = results[0]
    assert top.chain == "BTC"
    # Slug is now embedded in a "slug — description" entry, so check via substring.
    assert any("strip-ws" in r for r in top.repairs_applied)
    assert top.confidence == 85  # valid after minor repair


def test_strip_whitespace_emits_human_readable_trace():
    """Gap 5: repair trace must be human-readable, not a bare slug.

    The whitespace-strip entry should describe what was done in plain English
    (verb-led, includes the char count) so the ``--explain`` output and the web
    demo don't need code context to be meaningful.
    """
    results = classify("  1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa  \n")
    top = results[0]
    ws_entries = [r for r in top.repairs_applied if r.startswith("strip-ws")]
    assert ws_entries, f"expected a strip-ws entry, got {top.repairs_applied!r}"
    desc = ws_entries[0].split(" — ", 1)[1]
    assert desc.startswith("Stripped"), f"should lead with a verb, got {desc!r}"
    assert "chars of whitespace" in desc
    # Sanity: at least a few whitespace chars were removed from this input.
    assert any(token.isdigit() and int(token) > 0 for token in desc.split())


def test_cosmos_returns_cross_chain_alternates():
    # Generate a valid cosmos address for testing
    from ckc.validators.base import bech32_encode, convertbits
    hash160 = bytes(range(20))
    data_5bit = convertbits(list(hash160), 8, 5, True)
    cosmos_addr = bech32_encode("cosmos", data_5bit, "bech32")

    results = classify(cosmos_addr)
    top = results[0]
    assert top.chain == "ATOM"
    assert len(top.cross_chain_alternates) >= 5


def test_garbage_returns_empty():
    results = classify("hello world this is not a key")
    assert results == []


def test_chains_filter():
    cfg = Config(chains={"ETH"})
    results = classify("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", config=cfg)
    assert results == []  # BTC filtered out


def test_min_confidence_filter():
    cfg = Config(min_confidence=80)
    # SOL address caps at 50 — should be filtered out
    results = classify("dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc", config=cfg)
    assert results == []


def test_no_duplicate_matches():
    """Regression for Issue #2: preprocessor emits multiple candidates
    (raw / lower / upper) that all validate against EVMValidator for an
    EIP-55 address. The pipeline must emit exactly one ETH/address-eip55
    match, not duplicates."""
    results = classify("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
    eth_eip55 = [m for m in results if m.chain == "ETH" and m.format == "address-eip55"]
    assert len(eth_eip55) == 1
