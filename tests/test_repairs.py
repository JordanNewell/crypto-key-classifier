from ckc.repairs import MAX_CANDIDATES, encoding_variants, length_repairs, ocr_substitutions


def test_ocr_substitutions_single_char():
    # "O" in a numeric context should yield a "0" variant
    variants = ocr_substitutions("O123")
    normalizeds = [v.normalized for v in variants]
    assert "0123" in normalizeds
    assert all("ocr:" in r for v in variants for r in v.repairs if v.normalized == "0123")


def test_ocr_substitutions_multiple_chars():
    # Each confusable produces a separate variant; we do not chain in one stage
    variants = ocr_substitutions("OISS")
    normalizeds = {v.normalized for v in variants}
    # "O→0", "I→1", "S→5" — at minimum the one-char swaps
    assert "0ISS" in normalizeds
    assert "O1SS" in normalizeds
    assert "OI55" in normalizeds or "OIS5" in normalizeds


def test_encoding_variants_hex_to_bytes():
    variants = encoding_variants("deadbeef")
    # Should at least try to decode as hex and produce bytes
    assert any(v.bytes_value == b"\xde\xad\xbe\xef" for v in variants)


def test_encoding_variants_base58_to_bytes():
    # "tjXPSa" base58 decode is well-defined (Bitcoin alphabet excludes 0/O/I/l)
    variants = encoding_variants("tjXPSa")
    assert any(v.bytes_value is not None and len(v.bytes_value) > 0 for v in variants)


def test_length_repairs_insert():
    # If target length is 4 and we have "abc", insert one char at each position
    variants = length_repairs("abc", target_lengths={4})
    normalizeds = {v.normalized for v in variants}
    # We don't predict WHICH char — we just produce position slots
    # The validator is responsible for trying checksums on these
    assert all(len(n) == 4 for n in normalizeds)


def test_max_candidates_constant_exists():
    assert isinstance(MAX_CANDIDATES, int)
    assert MAX_CANDIDATES == 50
