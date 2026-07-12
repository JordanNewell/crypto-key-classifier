"""Property tests: generate valid MVP-chain keys, mutate, verify recovery.

Target recovery rates per spec:
- whitespace pollution: 100%
- OCR substitution: >=80%
- char swap (same charset): >=50%
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings

from ckc.pipeline import classify

from .mutations import whitespace_pollution
from .strategies import (
    btc_bech32_strategy,
    btc_p2pkh_strategy,
    btc_p2sh_strategy,
    cosmos_address_strategy,
    doge_p2pkh_strategy,
    eth_address_strategy,
    eth_privkey_strategy,
    ltc_p2pkh_strategy,
    solana_address_strategy,
)


def _top_chain(corrupted: str) -> str | None:
    """Run pipeline on corrupted input, return top match's chain or None."""
    results = classify(corrupted)
    return results[0].chain if results else None


# --- Whitespace pollution: should ALWAYS be recovered (Stage 1 strip-ws) ---


@given(btc_p2pkh_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_btc_p2pkh_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(eth_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_eth_address_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(solana_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_solana_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(cosmos_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_cosmos_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


# --- Sanity: original (unmutated) key MUST classify correctly ---


@given(btc_p2pkh_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_btc_p2pkh_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(btc_bech32_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_btc_bech32_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(ltc_p2pkh_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_ltc_p2pkh_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(doge_p2pkh_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_doge_p2pkh_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(eth_privkey_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_eth_privkey_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(btc_p2sh_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_btc_p2sh_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


# --- Aggregated whitespace test (covers all MVP chains at once) ---


@given(
    btc_p2pkh_strategy() | btc_p2sh_strategy() | btc_bech32_strategy() |
    ltc_p2pkh_strategy() | doge_p2pkh_strategy() |
    eth_address_strategy() | eth_privkey_strategy() |
    solana_address_strategy() | cosmos_address_strategy()
)
@settings(max_examples=200, deadline=None, suppress_health_check=list(HealthCheck))
def test_all_mvp_chains_whitespace_recovered(item):
    """All MVP-chain keys should survive whitespace pollution."""
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain, f"failed for {chain}: {addr!r} -> {corrupted!r}"
