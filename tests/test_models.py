from ckc.models import Candidate, Match


def test_candidate_minimal():
    c = Candidate(raw="abc", normalized="abc", repairs=[], encoding=None, bytes_value=None)
    assert c.raw == "abc"
    assert c.repairs == []


def test_candidate_with_repairs():
    c = Candidate(
        raw=" abc ",
        normalized="abc",
        repairs=["strip-ws"],
        encoding="base58",
        bytes_value=b"\x01",
    )
    assert c.repairs == ["strip-ws"]
    assert c.bytes_value == b"\x01"


def test_match_full():
    m = Match(
        chain="BTC",
        format="P2PKH",
        key_type="address",
        confidence=100,
        checksum_status="valid",
        network="mainnet",
        cross_chain_alternates=[("LTC", "Labc...")],
        wallet_compatibility=["Electrum"],
        repairs_applied=[],
        notes=[],
    )
    assert m.chain == "BTC"
    assert m.confidence == 100
