"""Wallet compatibility lists per chain.

Seeded from each chain's official docs. Not exhaustive — accurate.
Names are the user-facing wallet brand, not package IDs.
"""

WALLETS: dict[str, list[str]] = {
    # BTC family (BTC, LTC, DOGE, BCH share most wallets)
    "BTC": [
        "Bitcoin Core", "Electrum", "Sparrow", "Blue Wallet",
        "Wasabi", "Ledger", "Trezor", "Coldcard",
    ],
    "LTC": ["Electrum-LTC", "Litecoin Core", "Ledger", "Trezor", "Exodus"],
    "DOGE": ["Dogecoin Core", "MultiDoge", "Ledger", "Trezor"],
    "BCH": ["Bitcoin Cash Node", "Electron Cash", "Ledger", "Trezor"],
    # EVM family
    "ETH": [
        "MetaMask", "Trust Wallet", "Ledger", "Trezor",
        "MyEtherWallet", "Rainbow", "Coinbase Wallet", "Rabby",
    ],
    # Solana
    "SOL": ["Phantom", "Solflare", "Backpack", "Ledger"],
    # Cosmos IBC (all use Keplr + Ledger Cosmos app)
    "ATOM": ["Keplr", "Ledger", "Cosmostation", "Leap"],
    "OSMO": ["Keplr", "Ledger"],
    "JUNO": ["Keplr", "Ledger"],
    "AKT": ["Keplr", "Ledger"],
    "INJ": ["Keplr", "Ledger"],
}


def wallets_for(chain: str) -> list[str]:
    """Return wallet compatibility list for a chain code."""
    return WALLETS.get(chain.upper(), [])
