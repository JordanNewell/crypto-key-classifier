"""End-to-end smoke tests for long-tail validators (Plan 2)."""

from ckc.pipeline import Config, classify


def test_e2e_tron():
    from ckc.validators.base import base58check_encode
    addr = base58check_encode(b"\x41" + bytes(range(20)))
    r = classify(addr)
    assert r and r[0].chain == "TRX"


def test_e2e_ripple():
    from ckc.validators.ripple import ripple_base58check_encode
    addr = ripple_base58check_encode(b"\x00" + bytes(range(20)))
    r = classify(addr)
    assert r and r[0].chain == "XRP"


def test_e2e_algorand():
    from ckc.validators.algorand import algorand_encode_address
    addr = algorand_encode_address(bytes(range(32)))
    r = classify(addr)
    assert r and r[0].chain == "ALGO"


def test_e2e_tezos():
    from ckc.validators.base import base58check_encode
    addr = base58check_encode(bytes.fromhex("06a19f") + bytes(range(20)))
    r = classify(addr)
    assert r and r[0].chain == "XTZ"


def test_e2e_polkadot():
    from ckc.validators.polkadot import ss58_encode
    addr = ss58_encode(0, bytes(range(32)))
    r = classify(addr)
    assert r and r[0].chain == "DOT"


def test_e2e_kusama():
    from ckc.validators.polkadot import ss58_encode
    addr = ss58_encode(2, bytes(range(32)))
    r = classify(addr)
    assert r and r[0].chain == "KSM"


def test_e2e_stellar():
    from ckc.validators.stellar import stellar_encode
    addr = stellar_encode(b"\x30" + bytes(range(32)))
    r = classify(addr)
    assert r and r[0].chain == "XLM"


def test_e2e_ton():
    from ckc.validators.ton import ton_encode
    addr = ton_encode(bytes([0x11, 0]) + bytes(range(32)))
    r = classify(addr)
    assert r and r[0].chain == "TON"


def test_e2e_cardano():
    from ckc.validators.base import bech32_encode, convertbits
    data_5bit = convertbits(list(bytes(range(28))), 8, 5, True)
    assert data_5bit is not None
    addr = bech32_encode("addr1", data_5bit, "bech32")
    r = classify(addr)
    assert r and r[0].chain == "ADA"


def test_e2e_monero():
    from ckc.validators.base import keccak256
    from ckc.validators.monero import monero_encode_address
    payload = b"\x12" + bytes(range(32)) + bytes(range(32, 64))
    addr = monero_encode_address(payload + keccak256(payload)[:4])
    r = classify(addr)
    assert r and r[0].chain == "XMR"


def test_e2e_kaspa():
    from ckc.validators.base import bech32_encode, convertbits
    data_5bit = convertbits(list(bytes(range(32))), 8, 5, True)
    assert data_5bit is not None
    addr = bech32_encode("kaspa", data_5bit, "bech32")
    r = classify(addr)
    assert r and r[0].chain == "KAS"


def test_e2e_sui_aptos():
    # NOTE: 0x + 64 hex is structurally identical to EVM private key (confidence 100).
    # Use chain filter to scope to SUI/APT only — also exercises the new pipeline
    # chains_covered logic.
    addr = "0x" + "1" * 64
    r = classify(addr, Config(chains={"SUI", "APT"}))
    assert r and r[0].chain in {"SUI", "APT"}


def test_e2e_near_implicit():
    # NOTE: 64 lowercase hex is structurally identical to EVM private key (confidence 100).
    # Use chain filter to scope to NEAR only — also exercises the new pipeline
    # chains_covered logic.
    addr = "a" * 64
    r = classify(addr, Config(chains={"NEAR"}))
    assert r and r[0].chain == "NEAR"


def test_e2e_all_validators_discovered():
    """All 17 validators (4 MVP + 12 long-tail + 1 mnemonic) should be in the registry."""
    from ckc.validators import all_validators
    count = len(all_validators())
    assert count == 17, f"expected 17 validators, got {count}"


def test_e2e_garbage_returns_empty():
    assert classify("hello world not a key") == []
