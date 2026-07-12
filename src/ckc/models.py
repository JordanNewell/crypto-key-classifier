"""Core data models for the classifier pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    """A normalized variant of an input string being tested against validators."""

    raw: str
    normalized: str
    repairs: list[str]
    encoding: str | None
    bytes_value: bytes | None


@dataclass
class Match:
    """A successful classification of an input as a particular chain/format."""

    chain: str
    format: str
    key_type: str  # "address" | "private-key" | "public-key" | "mnemonic"
    confidence: int  # 0-100
    checksum_status: str  # "valid" | "failed" | "none" | "skipped"
    network: str | None
    cross_chain_alternates: list[tuple[str, str]] = field(default_factory=list)
    wallet_compatibility: list[str] = field(default_factory=list)
    repairs_applied: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
