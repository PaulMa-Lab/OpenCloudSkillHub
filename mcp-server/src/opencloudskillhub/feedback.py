"""Course feedback collection — append-only, Hub-local.

Agents report back: install succeeded/failed, capability missing, or (most valuable)
guide-does-not-match-reality. Milestone 6 keeps this deliberately simple: append a
JSON line to a Hub-local log for humans to review. There is NO automated learning
loop (ADR-004): feedback informs human course iteration, it does not auto-modify
guides or auto-change trust.

Writing here touches only the Hub's own storage (registry/feedback/*.jsonl), never
the user's machine — so it needs no user approval.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import find_repo_root

# Recommended (not enforced) outcome vocabulary.
OUTCOMES = (
    "installed",
    "verified",
    "used",
    "install_failed",
    "verify_failed",
    "missing_capability",
    "guide_mismatch",
)


def _default_dir() -> Path:
    return find_repo_root() / "registry" / "feedback"


def _safe_name(name: str | None) -> str:
    base = name or "_global"
    cleaned = "".join(c for c in base if c.isalnum() or c in "-_")
    return cleaned or "_global"


def submit_feedback(
    skill_id: str | None,
    outcome: str,
    *,
    stage: str | None = None,
    logs: str | None = None,
    guide_mismatch: str | None = None,
    notes: str | None = None,
    feedback_dir: str | Path | None = None,
) -> dict[str, Any]:
    record = {
        "id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(),
        "skill_id": skill_id,
        "outcome": outcome,
        "stage": stage,
        "logs": logs,
        "guide_mismatch": guide_mismatch,
        "notes": notes,
    }
    target_dir = Path(feedback_dir) if feedback_dir else _default_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{_safe_name(skill_id)}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "accepted": True,
        "id": record["id"],
        "path": str(path),
        "note": "已记录到平台本地日志，供人工迭代课程；不会自动修改 guide 或 trust。",
    }
