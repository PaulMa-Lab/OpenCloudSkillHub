"""Tests for milestone-5 generic execution-support tools + the OCR seed course."""

from __future__ import annotations

from pathlib import Path

from opencloudskillhub import exec_support
from opencloudskillhub.validate import validate_skill_id


def test_ocr_course_validates_clean() -> None:
    report = validate_skill_id("ocr")
    assert report is not None
    assert report["valid"] is True, report["errors"]
    assert report["warnings"] == [], report["warnings"]


def test_generate_install_plan_ocr_rapidocr() -> None:
    plan = exec_support.generate_install_plan("ocr")
    assert plan["profile_id"] == "rapidocr"  # default profile
    assert plan["env_path"].endswith(str(Path(".opencloudskillhub") / "envs" / "ocr"))
    step_ids = [s["id"] for s in plan["steps"]]
    assert "create_venv" in step_ids
    assert "install_requirements" in step_ids
    assert "smoke_test" in step_ids
    assert "generate_runner" in step_ids
    # the mutating steps must be approval-gated
    assert all(s["approval_required"] for s in plan["steps"] if s["id"] in {"create_venv", "install_requirements"})
    # rollback present for venv-creating step
    venv_step = next(s for s in plan["steps"] if s["id"] == "create_venv")
    assert venv_step["rollback"]


def test_generate_install_plan_unknown_profile() -> None:
    plan = exec_support.generate_install_plan("ocr", profile_id="nope")
    assert "error" in plan
    assert "rapidocr" in plan["available_profiles"]


def test_get_verification_plan_ocr() -> None:
    vp = exec_support.get_verification_plan("ocr")
    assert Path(vp["smoke_test"]).is_file()
    assert vp["expected"]["contains"] == ["HELLO", "OCR", "12345"]
    assert vp["run_command"].endswith('--smoke') is False  # full run, not smoke


def test_diagnose_error_matches_numpy() -> None:
    logs = "ImportError: A module compiled using NumPy 1.x cannot be run in NumPy 2.x ... _ARRAY_API not found"
    result = exec_support.diagnose_error("ocr", logs)
    ids = [m["id"] for m in result["matched"]]
    assert "numpy_incompat" in ids
    assert result["troubleshooting_resource"] == "skill://ocr/troubleshooting"


def test_diagnose_error_no_match() -> None:
    result = exec_support.diagnose_error("ocr", "totally unrelated message")
    assert result["matched"] == []


def test_detect_environment_skill_fit() -> None:
    info = exec_support.detect_environment("ocr")
    assert info["os"]  # non-empty
    assert info["skill_fit"]["skill_id"] == "ocr"
    # On this Windows dev machine the OCR course's platform should be supported.
    assert info["skill_fit"]["platform_supported"] is True
    assert "rapidocr" in info["skill_fit"]["profiles"]
