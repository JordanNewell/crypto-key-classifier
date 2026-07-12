"""Property tests for long-tail validators (Tron, Stellar, Polkadot, Monero)."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings

from ckc.pipeline import classify

from .mutations import whitespace_pollution
from .strategies import (
    monero_address_strategy,
    polkadot_address_strategy,
    stellar_account_strategy,
    tron_address_strategy,
)


def _top_chain(corrupted: str) -> str | None:
    results = classify(corrupted)
    return results[0].chain if results else None


@given(tron_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_tron_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(stellar_account_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_stellar_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(polkadot_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_polkadot_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(monero_address_strategy())
@settings(max_examples=50, deadline=None, suppress_health_check=list(HealthCheck))
def test_monero_whitespace_recovered(item):
    chain, addr = item
    corrupted = whitespace_pollution(addr)
    assert _top_chain(corrupted) == chain


@given(tron_address_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_tron_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(stellar_account_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_stellar_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(polkadot_address_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_polkadot_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain


@given(monero_address_strategy())
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_monero_classifies(item):
    chain, addr = item
    assert _top_chain(addr) == chain
