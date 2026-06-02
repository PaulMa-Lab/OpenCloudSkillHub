"""Tests for the remote-mode additions (transport-agnostic parts):
assess_environment, get_skill_asset, inlined requirements in install plans."""

from __future__ import annotations

import pytest

from opencloudskillhub import exec_support, registry


def test_assess_environment_good_fit() -> None:
    r = exec_support.assess_environment("ocr", {"os": "Windows", "python_version": "3.12.3"})
    assert r["platform_supported"] is True
    assert r["python_ok"] is True
    assert "rapidocr" in r["profiles"]


def test_assess_environment_bad_fit() -> None:
    r = exec_support.assess_environment("ocr", {"os": "Linux", "python_version": "3.14.0"})
    assert r["platform_supported"] is False  # OCR course is windows-only
    assert r["python_ok"] is False
    assert "3.14" in r["python_note"]


def test_assess_environment_partial_report() -> None:
    r = exec_support.assess_environment("ocr", {})
    assert r["platform_supported"] is None
    assert r["python_ok"] is None


def test_get_skill_asset_reads_requirements() -> None:
    content = registry.read_skill_asset("ocr", "requirements/rapidocr.txt")
    assert "rapidocr_onnxruntime" in content


def test_get_skill_asset_traversal_blocked() -> None:
    with pytest.raises(FileNotFoundError):
        registry.read_skill_asset("ocr", "../../secrets.txt")


def test_install_plan_inlines_packages() -> None:
    plan = exec_support.generate_install_plan("ocr")
    req_step = next(s for s in plan["steps"] if s["id"] == "install_requirements")
    assert "rapidocr_onnxruntime==1.4.4" in req_step["packages"]
    assert "rapidocr_onnxruntime==1.4.4" in req_step["command"]  # self-contained, no -r server path
    assert req_step["requirements_ref"] == "requirements/rapidocr.txt"
