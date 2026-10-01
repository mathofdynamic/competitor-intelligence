"""Dependency-free negative and invariants tests for the portable skill fixtures."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def iso(value: str) -> None:
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_source(source: dict) -> None:
    assert source["id"].startswith("src_")
    assert source["url"].startswith("https://")
    assert source["status"] in {"candidate", "unverified", "verified", "stale", "blocked", "rejected"}
    iso(source["discoveredAt"])
    iso(source["observedAt"])
    assert source["collection"]["robots"] != "disallowed"
    assert len(source["evidence"]["sha256"]) == 64


def validate_finding(finding: dict, source_status: str) -> None:
    assert finding["id"].startswith("find_")
    assert len(finding["observedText"]) >= 12
    iso(finding["observation"]["observedAt"])
    assert 0 <= finding["confidence"] <= 1
    if finding["status"] == "approved":
        assert source_status == "verified", "unverified sources cannot produce approved findings"
        assert finding.get("review"), "approved findings require a human review decision"


def main() -> None:
    source = load("source-valid.json")
    finding = load("finding-valid.json")
    validate_source(source)
    validate_finding(finding, source["status"])

    invalid = load("finding-invalid-unverified-source.json")
    try:
        validate_finding(invalid, "unverified")
    except AssertionError:
        pass
    else:
        raise AssertionError("negative fixture was accepted")

    assert load("source-valid.json")["status"] == "verified"
    print("competitor skill fixtures: PASS (valid source/finding and rejected approval bypass)")


if __name__ == "__main__":
    main()
