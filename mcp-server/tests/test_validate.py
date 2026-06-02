"""Tests for validate_skill_package against fixtures.

Run from the venv:
    python -m pytest mcp-server/tests -q
"""

from __future__ import annotations

from pathlib import Path

from opencloudskillhub.validate import validate_package_dir, validate_skill_id

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _codes(findings: list[dict]) -> set[str]:
    return {f["code"] for f in findings}


def test_good_skill_is_valid() -> None:
    report = validate_package_dir(FIXTURES / "good-skill")
    assert report["valid"] is True, report["errors"]
    assert report["errors"] == []
    assert report["skill_id"] == "good"


def test_bad_skill_reports_expected_errors() -> None:
    report = validate_package_dir(FIXTURES / "bad-skill")
    assert report["valid"] is False
    error_codes = _codes(report["errors"])
    # risk floor, missing network for download, missing file, traversal, self-declared trust, dangling profile ref
    assert {"R-SAFE-1", "R-SAFE-2", "R-REF-1", "R-REF-2", "R-GOV-1", "R-REF-4"} <= error_codes, error_codes
    warn_codes = _codes(report["warnings"])
    assert {"R-CONS-2", "R-CONS-3", "R-GOV-3"} <= warn_codes, warn_codes


def test_missing_manifest_is_struct_error() -> None:
    report = validate_package_dir(FIXTURES / "does-not-exist")
    assert report["valid"] is False
    assert _codes(report["errors"]) == {"R-STRUCT-1"}


def test_validate_skill_id_unknown_returns_none() -> None:
    assert validate_skill_id("definitely-not-a-real-skill-id") is None
