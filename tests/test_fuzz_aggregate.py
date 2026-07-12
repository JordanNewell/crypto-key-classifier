"""Aggregate fuzz report: run many random tests, count recovery rates."""

from __future__ import annotations

import random

from ckc.pipeline import classify
from tests.fuzz.mutations import (
    case_flip,
    char_swap_adjacent,
    ocr_substitute,
    whitespace_pollution,
)
from tests.fuzz.strategies import (
    btc_p2pkh_strategy,
    cosmos_address_strategy,
    eth_address_strategy,
    monero_address_strategy,
    solana_address_strategy,
    tron_address_strategy,
)

STRATEGIES = [
    btc_p2pkh_strategy, eth_address_strategy, solana_address_strategy,
    cosmos_address_strategy, tron_address_strategy, monero_address_strategy,
]


def _make_one(strategy_fn):
    """Draw one sample from a strategy (uses hypothesis find)."""
    from hypothesis import find
    return find(strategy_fn(), lambda x: True)


def test_whitespace_recovery_100_percent():
    """Whitespace pollution recovery target: 100%."""
    random.seed(1)
    passed = 0
    total = 30
    for _ in range(total):
        strat = random.choice(STRATEGIES)
        chain, addr = _make_one(strat)
        corrupted = whitespace_pollution(addr)
        results = classify(corrupted)
        if results and results[0].chain == chain:
            passed += 1
    recovery = passed / total
    assert recovery == 1.0, f"whitespace recovery {recovery:.0%} < 100%"


def test_overall_recovery_above_threshold():
    """At least 40% of single-mutation corruptions should be recovered."""
    random.seed(1)
    mutations = [case_flip, char_swap_adjacent, ocr_substitute, whitespace_pollution]
    passed = 0
    total = 60
    skipped = 0
    for _ in range(total):
        strat = random.choice(STRATEGIES)
        mutation = random.choice(mutations)
        chain, addr = _make_one(strat)
        corrupted = mutation(addr)
        if corrupted == addr:
            skipped += 1
            continue
        results = classify(corrupted)
        if results and results[0].chain == chain:
            passed += 1
    effective_total = total - skipped
    recovery = passed / effective_total if effective_total else 0
    assert (
        recovery >= 0.4
    ), f"recovery {recovery:.0%} < 40% (passed={passed}/{effective_total}, skipped={skipped})"
