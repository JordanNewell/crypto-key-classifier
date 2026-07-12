from ckc.validators.base import levenshtein_distance


def test_identical_strings():
    assert levenshtein_distance("abc", "abc") == 0


def test_one_substitution():
    assert levenshtein_distance("abc", "abd") == 1


def test_one_insertion():
    assert levenshtein_distance("abc", "abcd") == 1


def test_one_deletion():
    assert levenshtein_distance("abc", "ab") == 1


def test_completely_different():
    assert levenshtein_distance("abc", "xyz") == 3


def test_typo_distance_one():
    # Common BIP39 typo: "abondon" → "abandon"
    assert levenshtein_distance("abondon", "abandon") == 1


def test_empty_strings():
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("abc", "") == 3
