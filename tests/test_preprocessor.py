from ckc.preprocessor import preprocess


def test_strip_whitespace():
    cands = preprocess("  hello  ")
    assert len(cands) >= 1
    assert cands[0].normalized == "hello"
    assert "strip-ws" in cands[0].repairs


def test_strip_unicode_whitespace():
    # Zero-width space + non-breaking space + newline
    cands = preprocess("​abc\xa0\n")
    assert cands[0].normalized == "abc"


def test_drops_0x_prefix():
    cands = preprocess("0xdeadbeef")
    variants = [c.normalized for c in cands]
    assert "deadbeef" in variants
    # original-with-prefix also retained in case the format wants it (ETH)
    assert "0xdeadbeef" in variants


def test_case_variants():
    cands = preprocess("ABCDEF")
    variants = [c.normalized for c in cands]
    assert "abcdef" in variants
    assert "ABCDEF" in variants


def test_dedupes():
    # whitespace strip on "abc" produces same as identity — no duplicate candidates
    cands = preprocess("abc")
    normalizeds = [c.normalized for c in cands]
    assert len(normalizeds) == len(set(normalizeds))
