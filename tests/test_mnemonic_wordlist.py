"""Verify the bundled BIP-39 English wordlist is the official one."""
from importlib import resources


def test_wordlist_has_2048_words():
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        words = [line.strip() for line in f if line.strip()]
    assert len(words) == 2048


def test_wordlist_sorted():
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        words = [line.strip() for line in f if line.strip()]
    assert words == sorted(words)


def test_wordlist_first_word():
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        first = f.readline().strip()
    assert first == "abandon"


def test_wordlist_last_word():
    with resources.files("ckc.data").joinpath("bip39_english.txt").open() as f:
        words = [line.strip() for line in f if line.strip()]
    assert words[-1] == "zoo"
