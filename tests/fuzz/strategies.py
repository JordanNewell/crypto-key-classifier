"""Hypothesis strategies: generate valid keys per chain.

Each strategy produces a (chain_code, valid_key_string) tuple using the same
encode functions the validators use. This ensures we're testing valid inputs.
"""

from __future__ import annotations

import os

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from ckc.validators.base import (
    base58check_encode,
    bech32_encode,
    convertbits,
    crc16_xmodem,
    keccak256,
    monero_base58_encode,
)


def _random_bytes(n: int) -> bytes:
    return bytes(os.urandom(n))


# --- BTC family ---


def btc_p2pkh_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid BTC P2PKH addresses."""
    return st.builds(
        lambda _: ("BTC", base58check_encode(b"\x00" + _random_bytes(20))),
        st.none(),
    )


def btc_p2sh_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("BTC", base58check_encode(b"\x05" + _random_bytes(20))),
        st.none(),
    )


def btc_bech32_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid BTC bech32 segwit v0 addresses (20-byte witness program)."""
    def make(_) -> tuple[str, str]:
        program = _random_bytes(20)
        data = [0] + convertbits(list(program), 8, 5, True)
        return ("BTC", bech32_encode("bc", data, "bech32"))
    return st.builds(make, st.none())


def ltc_p2pkh_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("LTC", base58check_encode(b"\x30" + _random_bytes(20))),
        st.none(),
    )


def doge_p2pkh_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("DOGE", base58check_encode(b"\x1e" + _random_bytes(20))),
        st.none(),
    )


# --- EVM ---


def eth_address_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid ETH addresses (all-lowercase, no EIP-55 checksum)."""
    return st.builds(
        lambda _: ("ETH", "0x" + _random_bytes(20).hex()),
        st.none(),
    )


def eth_privkey_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("ETH", "0x" + _random_bytes(32).hex()),
        st.none(),
    )


# --- Solana ---


def solana_address_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid SOL addresses (32-byte ed25519 base58)."""
    import base58
    return st.builds(
        lambda _: ("SOL", base58.b58encode(_random_bytes(32)).decode("ascii")),
        st.none(),
    )


# --- Cosmos (one HRP representative) ---


def cosmos_address_strategy() -> SearchStrategy[tuple[str, str]]:
    def make(_) -> tuple[str, str]:
        hash160 = _random_bytes(20)
        data = convertbits(list(hash160), 8, 5, True)
        return ("ATOM", bech32_encode("cosmos", data, "bech32"))
    return st.builds(make, st.none())


# --- Long-tail representatives ---


def tron_address_strategy() -> SearchStrategy[tuple[str, str]]:
    return st.builds(
        lambda _: ("TRX", base58check_encode(b"\x41" + _random_bytes(20))),
        st.none(),
    )


def stellar_account_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid Stellar G... accounts (version 0x30 + 32-byte pubkey + CRC16)."""
    import base64
    def make(_) -> tuple[str, str]:
        payload = b"\x30" + _random_bytes(32)
        checksum = crc16_xmodem(payload).to_bytes(2, "big")
        full = payload + checksum
        encoded = base64.b32encode(full).decode("ascii").rstrip("=")
        return ("XLM", encoded)
    return st.builds(make, st.none())


def polkadot_address_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid Polkadot SS58 addresses."""
    from ckc.validators.polkadot import ss58_encode
    def make(_) -> tuple[str, str]:
        pubkey = _random_bytes(32)
        return ("DOT", ss58_encode(0, pubkey))
    return st.builds(make, st.none())


def monero_address_strategy() -> SearchStrategy[tuple[str, str]]:
    """Generate valid Monero mainnet addresses."""
    def make(_) -> tuple[str, str]:
        payload = b"\x12" + _random_bytes(32) + _random_bytes(32)
        checksum = keccak256(payload)[:4]
        full = payload + checksum
        return ("XMR", monero_base58_encode(full))
    return st.builds(make, st.none())


# Aggregated strategy — picks a random chain
ALL_STRATEGIES = [
    btc_p2pkh_strategy(), btc_p2sh_strategy(), btc_bech32_strategy(),
    ltc_p2pkh_strategy(), doge_p2pkh_strategy(),
    eth_address_strategy(), eth_privkey_strategy(),
    solana_address_strategy(), cosmos_address_strategy(),
    tron_address_strategy(), stellar_account_strategy(),
    polkadot_address_strategy(), monero_address_strategy(),
]


def any_chain_strategy() -> SearchStrategy[tuple[str, str]]:
    """Pick any chain's strategy at random."""
    return st.one_of(*ALL_STRATEGIES)
