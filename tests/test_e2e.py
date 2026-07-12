"""End-to-end smoke tests exercising real input through the full pipeline.

Covers the headline scenarios from the spec:
  - Clean BTC address
  - BTC address with whitespace
  - ETH EIP-55 checksum valid
  - Solana address
  - Cosmos address with cross-chain alternates (generated)
  - Garbage input
  - Pipeline runs all validators without crashing
"""

from ckc.pipeline import classify


def test_e2e_clean_btc():
    matches = classify("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert matches and matches[0].chain == "BTC" and matches[0].confidence == 100


def test_e2e_btc_with_whitespace():
    matches = classify("  1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n\t")
    assert matches and matches[0].chain == "BTC"
    assert any("strip-ws" in r for r in matches[0].repairs_applied)


def test_e2e_eth_eip55_valid():
    matches = classify("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
    assert matches and matches[0].chain == "ETH" and matches[0].checksum_status == "valid"


def test_e2e_solana_address():
    matches = classify("dDCQNQXeMSaKwBPPnYiM6QXVi3PjDTW154H6pgKVmYc")
    assert matches and matches[0].chain == "SOL" and matches[0].confidence == 50


def test_e2e_cosmos_cross_chain_alternates():
    # Generate a valid cosmos address for testing
    from ckc.validators.base import bech32_encode, convertbits
    hash160 = bytes(range(20))
    data_5bit = convertbits(list(hash160), 8, 5, True)
    cosmos_addr = bech32_encode("cosmos", data_5bit, "bech32")

    matches = classify(cosmos_addr)
    assert matches and matches[0].chain == "ATOM"
    alt_chains = [c for c, _ in matches[0].cross_chain_alternates]
    assert "OSMO" in alt_chains
    assert "JUNO" in alt_chains


def test_e2e_garbage_input_returns_empty():
    assert classify("hello world this is not a key") == []
    assert classify("") == []
    assert classify("   ") == []


def test_e2e_pipeline_runs_all_validators_without_crashing():
    # Fuzz-ish: a wide range of inputs should not raise
    inputs = [
        "", "abc", "0x", "1A1zP1", "bc1q", "cosmos1",
        "5Kb8" * 13,  # long base58
        "deadbeef" * 8,  # long hex
        "0" * 100,
        "1" * 100,
    ]
    for raw in inputs:
        classify(raw)  # must not raise
