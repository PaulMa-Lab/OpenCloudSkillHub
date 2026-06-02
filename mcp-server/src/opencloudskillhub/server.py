"""OpenCloudSkillHub MCP server (platform core).

Milestone 1: a connectable FastMCP server (official mcp SDK) that
- exposes the system-level resources (system://guide, school://curriculum,
  system://changelog, skills://catalog), and
- offers the generic, read-only catalog tools (list_skills, search_skills,
  get_skill_detail).

Everything here is skill-agnostic (ADR-003). There are deliberately NO
skill-specific tools (no install_ocr / verify_ocr). The mutating, host-side
tools (generate_install_plan, get_verification_plan, diagnose_error, ...) and
manifest validation arrive in later milestones — and they remain generic,
parameterized by skill_id.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import exec_support, feedback, registry
from .paths import read_text
from .validate import validate_package_dir, validate_skill_id

INSTRUCTIONS = (
    "OpenCloudSkillHub is a capability hub / agent school. It does NOT execute "
    "anything on the user's machine — it provides knowledge (resources) and "
    "read-only computation (tools); YOU execute install/verify steps with your "
    "own tools, only after user approval.\n\n"
    "Before using any skill, READ the resource system://guide (rules + map), "
    "then school://curriculum (how to learn any course). Then browse "
    "skills://catalog or call search_skills to pick a course.\n\n"
    "For DOMAIN work (recruiting, e-commerce, finance...) rather than a general "
    "skill, call recommend_learning_path first: the Hub points you to the right "
    "domain system (e.g. RecruitOS) and what to read at ITS own MCP. The Hub only "
    "points — it does not host domain knowledge or hold task state.\n\n"
    "Dangerous actions (installing deps, running shell, writing files, "
    "downloading models, reading local files, uploading to remote services, and "
    "CONNECTING to a domain system's MCP endpoint) require explicit user approval. "
    "Read-only browsing/diagnosis does not."
)

mcp = FastMCP("OpenCloudSkillHub", instructions=INSTRUCTIONS)


# --- System-level resources (read-only knowledge) ---------------------------

@mcp.resource("system://guide", mime_type="text/markdown")
def system_guide() -> str:
    """Platform rules and entry point. The first thing an agent should read."""
    return read_text("system/guide.md")


@mcp.resource("school://curriculum", mime_type="text/markdown")
def school_curriculum() -> str:
    """The generic, skill-agnostic method for learning any single course."""
    return read_text("system/curriculum.md")


@mcp.resource("school://handoff-model", mime_type="text/markdown")
def school_handoff_model() -> str:
    """Teaching spec for explicit human/agent handoff (Auto/Approval/Human/Connector
    tasks). The Hub teaches the vocabulary only — task STATE lives in domain systems."""
    return read_text("system/handoff-model.md")


@mcp.resource("system://changelog", mime_type="text/markdown")
def system_changelog() -> str:
    """Platform and course version changes; consult before reusing cached knowledge."""
    return read_text("system/changelog.md")


@mcp.resource("skills://catalog", mime_type="application/json")
def skills_catalog() -> str:
    """Index of all available courses (skill packages), derived from manifests,
    annotated with each package's validation status."""
    return json.dumps({"skills": registry.catalog(with_validation=True)}, ensure_ascii=False, indent=2)


@mcp.resource("skill://{skill_id}/{doc}", mime_type="text/markdown")
def skill_resource(skill_id: str, doc: str) -> str:
    """Serve a course's guide doc (e.g. skill://ocr/guide, skill://ocr/install_windows).
    The <doc> keys come from the course manifest's `resources`. Read-only."""
    return registry.read_skill_resource(skill_id, doc)


@mcp.resource("domains://catalog", mime_type="application/json")
def domains_catalog() -> str:
    """Directory of registered domain systems (RecruitOS, etc.). These are pointers
    only — each domain's guide/knowledge/state lives at its OWN MCP endpoint, not here."""
    return json.dumps({"domains": registry.domain_catalog(with_validation=True)}, ensure_ascii=False, indent=2)


# --- Generic, read-only catalog tools ---------------------------------------

@mcp.tool()
def list_skills(status: str | None = None) -> list[dict[str, Any]]:
    """List available skills (courses). Optionally filter by status
    (draft|active|deprecated). Read-only; no approval needed.
    Tip: read system://guide first if you have not."""
    return registry.list_skills(status=status)


@mcp.tool()
def search_skills(query: str, tags: list[str] | None = None) -> list[dict[str, Any]]:
    """Search skills by free-text query (matches id/name/summary/capabilities/tags)
    and optional required tags. Read-only; no approval needed."""
    return registry.search_skills(query, tags)


@mcp.tool()
def get_skill_detail(skill_id: str) -> dict[str, Any] | None:
    """Get a skill's full detail: public manifest, derived resource URIs
    (skill://<id>/<key>), required host capabilities, and risk level.
    Returns null if the skill id is unknown. Read-only; no approval needed."""
    return registry.get_skill_detail(skill_id)


@mcp.tool()
def list_domain_systems() -> list[dict[str, Any]]:
    """List registered domain systems (e.g. RecruitOS). Each entry is a pointer +
    trust + validation status — NOT the domain's content. Read-only; no approval."""
    return registry.domain_catalog(with_validation=True)


@mcp.tool()
def get_domain_system_detail(domain_id: str) -> dict[str, Any] | None:
    """Get a domain system's registration card: how_to_enter (mcp_endpoint, what to
    read first AT THE DOMAIN'S MCP), required general skills, trust, approval note.
    Null if unknown. Read-only — but actually CONNECTING to the endpoint needs user approval."""
    return registry.get_domain_detail(domain_id)


@mcp.tool()
def recommend_learning_path(task: str) -> dict[str, Any]:
    """Given a natural-language task, suggest where to learn: candidate domain systems
    (for domain work) and general skills (OCR/PDF/...), each WITH matching evidence.
    This is declarative keyword matching, NOT a verdict and NOT an LLM router — YOU
    (the agent) decide. Connecting to a domain MCP or installing a skill needs approval.
    Read-only; no approval needed to call."""
    return registry.recommend_learning_path(task)


@mcp.tool()
def detect_environment(skill_id: str | None = None) -> dict[str, Any]:
    """Probe the local machine (OS/arch/Python interpreters/disk). Optionally pass a
    skill_id to also get a fit check (platform supported? required host tools? profiles?).
    Reflects the machine the Hub runs on (= the user's machine for local stdio).
    Read-only; no approval needed."""
    return exec_support.detect_environment(skill_id)


@mcp.tool()
def assess_environment(skill_id: str, env_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Remote-friendly fit check: YOU report your environment (os, python_version, arch,
    disk_free_mb, in_venv) and the Hub judges whether the skill fits. Use this instead of
    detect_environment when the Hub is remote (it cannot probe your machine). Read-only."""
    return exec_support.assess_environment(skill_id, env_report)


@mcp.tool()
def get_skill_asset(skill_id: str, rel_path: str) -> dict[str, Any]:
    """Fetch the CONTENT of a course asset (e.g. assets/verify_ocr.py,
    requirements/rapidocr.txt, assets/runner_template.py) so you can run it locally.
    Needed when the Hub is remote and the file lives on the server. Read-only."""
    try:
        return {"skill_id": skill_id, "rel_path": rel_path, "content": registry.read_skill_asset(skill_id, rel_path)}
    except (FileNotFoundError, ValueError) as exc:
        return {"skill_id": skill_id, "rel_path": rel_path, "error": str(exc)}


@mcp.tool()
def generate_install_plan(skill_id: str, profile_id: str | None = None) -> dict[str, Any]:
    """Produce a step-by-step install PLAN for a skill+profile (does NOT execute).
    Each step carries risk / approval_required / rollback. The host runs the
    approved steps (model A). Pure computation; read-only; no approval to call."""
    return exec_support.generate_install_plan(skill_id, profile_id)


@mcp.tool()
def get_verification_plan(skill_id: str) -> dict[str, Any]:
    """Return how to verify a skill install: the smoke-test script path, the command
    to run it in the skill's venv, and the expected output. The host executes it and
    compares; the platform does not run skill code. Read-only; no approval to call."""
    return exec_support.get_verification_plan(skill_id)


@mcp.tool()
def diagnose_error(skill_id: str, logs: str) -> dict[str, Any]:
    """Match error logs against a skill's structured diagnostics (cause + actions + ref).
    Generic keyword matching; the OCR/skill knowledge lives in the course package.
    Read-only; no approval needed."""
    return exec_support.diagnose_error(skill_id, logs)


@mcp.tool()
def validate_skill_package(
    skill_id: str | None = None, package_path: str | None = None
) -> dict[str, Any] | None:
    """Validate a course package against the skill-package contract
    (docs/skill-package-contract.md): structure, referenced files, consistency,
    and safety/governance rules. Returns {skill_id, valid, errors, warnings,
    summary}; null if skill_id is given but unknown.

    Provide either skill_id (resolved under skills/) or an explicit package_path.
    Read-only; no approval needed."""
    if package_path:
        from pathlib import Path

        return validate_package_dir(Path(package_path))
    if skill_id:
        return validate_skill_id(skill_id)
    return {"error": "provide either skill_id or package_path"}


@mcp.tool()
def submit_skill_feedback(
    skill_id: str | None,
    outcome: str,
    stage: str | None = None,
    logs: str | None = None,
    guide_mismatch: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Report back on a course: outcome (installed|verified|used|install_failed|
    verify_failed|missing_capability|guide_mismatch), optional stage/logs/notes, and
    especially guide_mismatch (guide vs reality). Appended to a Hub-local log for human
    course iteration — NO auto-learning. Writes only Hub storage, not the user's machine;
    no user approval needed."""
    return feedback.submit_feedback(
        skill_id, outcome, stage=stage, logs=logs, guide_mismatch=guide_mismatch, notes=notes
    )


def main() -> None:
    """Entry point. Stdio by default; `--http` serves streamable-http (ADR-005)."""
    import sys

    if "--http" in sys.argv:
        from .serve_http import serve

        serve()
    else:
        mcp.run()


if __name__ == "__main__":
    main()
