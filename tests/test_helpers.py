from ckc.data.wallets import wallets_for
from ckc.validators.base import (
    blake2b,
    crc16_xmodem,
    monero_base58_decode,
    monero_base58_encode,
    sha512_256,
)


def test_crc16_xmodem_known_vector():
    # CRC16-XMODEM of b"123456789" is 0x31C3
    assert crc16_xmodem(b"123456789") == 0x31C3


def test_blake2b_known_vector():
    # BLAKE2b-256 of empty string
    expected = bytes.fromhex(
        "0e5751c026e543b2e8ab2eb06099daa1d1e5df47778f7787faab45cdf12fe3a8"
    )
    assert blake2b(b"", digest_size=32) == expected


def test_sha512_256_known_vector():
    # SHA512/256 of empty string (NIST variant, NOT SHA-512 truncated)
    expected = bytes.fromhex(
        "c672b8d1ef56ed28ab87c3622c5114069bdd3ad7b8f9737498d0c01ecef0967a"
    )
    assert sha512_256(b"") == expected


def test_monero_base58_round_trip():
    # 8-byte blocks → 11 chars each, last block carries remainder
    raw = bytes(range(66))  # 8 blocks of 8 bytes + 2 bytes remainder
    encoded = monero_base58_encode(raw)
    decoded = monero_base58_decode(encoded)
    assert decoded == raw


def test_monero_base58_block_boundary():
    # Encode a known Monero-shaped payload (network + 32 + 32 + checksum = 69 bytes)
    payload = b"\x12" + b"\x00" * 32 + b"\x01" * 32 + b"\xff" * 4
    encoded = monero_base58_encode(payload)
    assert len(encoded) == 95  # Monero mainnet address length
    decoded = monero_base58_decode(encoded)
    assert decoded == payload


def test_wallets_extended():
    # 14 new chains must be in the DB
    chains = [
        "XMR", "ADA", "XRP", "XLM", "TRX", "XTZ", "DOT",
        "KSM", "TON", "ALGO", "KAS", "SUI", "APT", "NEAR",
    ]
    for chain in chains:
        assert wallets_for(chain), f"missing wallet list for {chain}"
