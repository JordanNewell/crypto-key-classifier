"""Pipeline orchestrator.

For each input:
  1. Preprocess into candidate variants (Stage 1).
  2. For each validator: shape-match → strict validate → optional repairs.
  3. Collect matches, rank by confidence descending.
  4. Return ranked list.
"""

from __future__ import annotations

from dataclasses import dataclass

from ckc.models import Candidate, Match
from ckc.preprocessor import preprocess
from ckc.repairs import MAX_CANDIDATES, encoding_variants, ocr_substitutions
from ckc.validators import all_validators
from ckc.validators.base import Validator


@dataclass
class Config:
    """Pipeline configuration."""
    chains: set[str] | None = None  # None = all validators
    min_confidence: int = 0
    enable_repairs: bool = True
    max_repairs_per_input: int = MAX_CANDIDATES


def classify(raw: str, config: Config | None = None) -> list[Match]:
    """Classify a single input string. Returns ranked matches."""
    if not raw or not raw.strip():
        return []
    if config is None:
        config = Config()

    base_candidates = preprocess(raw)
    matches: list[Match] = []

    for validator in all_validators():
        # Filter by chain whitelist if set
        if config.chains is not None:
            validator_chains = _validator_chain_codes(validator)
            if not (validator_chains & config.chains):
                continue

        # Try base candidates first
        candidates = list(base_candidates)

        # Add format-specific repairs
        for base in base_candidates:
            candidates.extend(validator.suggest_repairs(base))

        # Cap total candidates
        candidates = candidates[: config.max_repairs_per_input]

        match_found = False
        for cand in candidates:
            if not validator.shape_match(cand):
                continue
            m = validator.validate(cand)
            if m is None:
                continue
            _adjust_confidence_for_repairs(m)
            if m.confidence >= config.min_confidence:
                matches.append(m)
            if m.checksum_status == "valid":
                match_found = True
                break  # stop repairing once checksum passes

        # If no match yet, try aggressive repairs (OCR, encoding)
        if not match_found and config.enable_repairs:
            aggressive = _generate_aggressive_candidates(base_candidates)
            for cand in aggressive[: config.max_repairs_per_input]:
                if not validator.shape_match(cand):
                    continue
                m = validator.validate(cand)
                if m is None:
                    continue
                _adjust_confidence_for_repairs(m)
                if m.confidence >= config.min_confidence:
                    matches.append(m)
                if m.checksum_status == "valid":
                    break

    # Dedup on (chain, format, confidence, checksum_status). Multiple preprocessor
    # variants (raw / lower / upper / hex-stripped) of the same input can all
    # validate and produce identical matches — keep only one of each.
    seen: set[tuple[str, str, int, str]] = set()
    deduped: list[Match] = []
    for m in matches:
        key = (m.chain, m.format, m.confidence, m.checksum_status)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(m)
    matches = deduped

    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches


def _validator_chain_codes(validator: Validator) -> set[str]:
    """Get all chain codes a validator can produce (for filtering)."""
    chain = getattr(validator, "chain", "")
    if chain == "BTC_FAMILY":
        return {"BTC", "LTC", "DOGE", "BCH"}
    if chain == "COSMOS_FAMILY":
        return {"ATOM", "OSMO", "JUNO", "AKT", "INJ", "EVMOS", "STRD", "REGEN", "XPRT"}
    if chain == "ETH":
        return {"ETH", "POLYGON", "ARBITRUM", "BASE", "OPTIMISM", "BSC", "AVALANCHE"}
    if chain == "SOL":
        return {"SOL"}
    return {chain}


def _generate_aggressive_candidates(base_candidates: list[Candidate]) -> list[Candidate]:
    """Apply OCR + encoding repairs to base candidates."""
    out: list[Candidate] = []
    for base in base_candidates:
        # OCR stage
        for ocr_cand in ocr_substitutions(base.normalized):
            ocr_cand.repairs = base.repairs + ocr_cand.repairs
            out.append(ocr_cand)

        # Encoding stage
        for enc_cand in encoding_variants(base.normalized):
            enc_cand.repairs = base.repairs + enc_cand.repairs
            out.append(enc_cand)

    return out


# Confidence tier constants — derived from spec doc
_MINOR_REPAIRS: set[str] = {
    "strip-ws",
    "lowercase",
    "uppercase",
    "drop-prefix:0x",
    "drop-prefix:0X",
    "unicode-nfc",
    "case:eip55",
}
_ENCODING_REPAIRS: set[str] = {
    "decode:hex",
    "decode:base58",
    "decode:base64",
}


def _adjust_confidence_for_repairs(m: Match) -> None:
    """Downgrade confidence based on which repairs were needed.

    Spec tiers:
      - No repairs + checksum valid → 100
      - Minor repairs (whitespace, case, prefix) + checksum valid → 85
      - Encoding repair + checksum valid → 70
      - OCR repair + checksum valid → 60

    No-op for matches with no repairs or non-valid checksum.
    """
    if not m.repairs_applied or m.checksum_status != "valid":
        return  # no repairs = 100 stays; non-valid checksum = don't touch

    repairs = m.repairs_applied
    if any(r.startswith("ocr:") for r in repairs):
        m.confidence = 60
    elif any(r in _ENCODING_REPAIRS for r in repairs):
        m.confidence = 70
    elif any(r in _MINOR_REPAIRS for r in repairs):
        m.confidence = 85
