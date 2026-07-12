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
    assert "strip-ws" in top.repairs_applied
    assert top.confidence == 85  # valid after minor repair


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
