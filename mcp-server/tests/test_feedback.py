"""Tests for submit_skill_feedback (append-only, Hub-local)."""

from __future__ import annotations

import json

from opencloudskillhub import feedback


def test_submit_feedback_writes_jsonl(tmp_path) -> None:
    r1 = feedback.submit_feedback(
        "ocr", "guide_mismatch", stage="install", notes="numpy pin was wrong", feedback_dir=tmp_path
    )
    assert r1["accepted"] is True
    assert r1["id"]

    r2 = feedback.submit_feedback("ocr", "verified", feedback_dir=tmp_path)
    assert r2["id"] != r1["id"]

    log = tmp_path / "ocr.jsonl"
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["skill_id"] == "ocr"
    assert rec["outcome"] == "guide_mismatch"
    assert rec["notes"] == "numpy pin was wrong"
    assert rec["ts"]  # timestamp present


def test_submit_feedback_global_and_sanitized_name(tmp_path) -> None:
    feedback.submit_feedback(None, "missing_capability", notes="need pdf-extraction", feedback_dir=tmp_path)
    assert (tmp_path / "_global.jsonl").is_file()

    feedback.submit_feedback("../evil", "installed", feedback_dir=tmp_path)
    # path traversal in the name must not escape the feedback dir
    written = [p.name for p in tmp_path.glob("*.jsonl")]
    assert "_global.jsonl" in written
    assert "evil.jsonl" in written  # '../' stripped
