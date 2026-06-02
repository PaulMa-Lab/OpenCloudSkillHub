"""Tests for the domain directory layer: validator + recommend_learning_path."""

from __future__ import annotations

from pathlib import Path

from opencloudskillhub import registry
from opencloudskillhub.validate import validate_domain_file

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "domains"


def _codes(findings: list[dict]) -> set[str]:
    return {f["code"] for f in findings}


def test_good_domain_is_valid() -> None:
    report = validate_domain_file(FIXTURES / "good-domain.yaml")
    assert report["valid"] is True, report["errors"]
    assert report["errors"] == []
    assert report["skill_id"] == "gooddomain"


def test_bad_domain_reports_expected_codes() -> None:
    report = validate_domain_file(FIXTURES / "bad-domain.yaml")
    assert report["valid"] is False
    # http endpoint, self-declared trust, invalid safety_level enum
    assert {"D-SAFE-1", "D-GOV-1", "D-STRUCT-4"} <= _codes(report["errors"]), report["errors"]
    # unknown required skill, draft status
    assert {"D-REF-1", "D-GOV-3"} <= _codes(report["warnings"]), report["warnings"]


def test_recommend_learning_path_finds_recruiting_domain() -> None:
    result = registry.recommend_learning_path("帮用户招聘一个电商运营")
    ids = [c["id"] for c in result["domain_candidates"]]
    assert "recruitos" in ids, result["domain_candidates"]
    recruitos = next(c for c in result["domain_candidates"] if c["id"] == "recruitos")
    assert "招聘" in recruitos["matched_terms"]
    assert recruitos["how_to_enter"]["mcp_endpoint"].startswith("https://")
    assert recruitos["trust"] == "official"


def test_recommend_learning_path_no_match_is_empty() -> None:
    result = registry.recommend_learning_path("xyzzy unrelated nonsense")
    assert result["domain_candidates"] == []


def test_recruitos_seed_registration_is_valid() -> None:
    from opencloudskillhub.validate import validate_domain_id

    report = validate_domain_id("recruitos")
    assert report is not None
    # The seed is valid; it only carries D-REF-1 warnings for not-yet-authored general skills.
    assert report["valid"] is True, report["errors"]
    assert _codes(report["warnings"]) <= {"D-REF-1"}
