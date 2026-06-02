"""Skill registry — scans skills/ and builds the catalog.

This is the ONLY part of the platform that reads skill packages, and it reads
them as DATA: it parses each skill.yaml manifest and exposes generic, derived
views (catalog entries, detail). It never imports or executes skill code, and
it contains no skill-specific domain logic (ADR-003).

Milestone 1 scope: tolerant scanning + list/search/detail over manifests.
Full manifest validation (validate_skill_package, the contract in
docs/skill-package-contract.md) lands in milestone 2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .paths import find_repo_root


def _skills_dir() -> Path:
    return find_repo_root() / "skills"


def _load_manifest(skill_dir: Path) -> dict[str, Any] | None:
    manifest_file = skill_dir / "skill.yaml"
    if not manifest_file.is_file():
        return None
    try:
        data = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        # A malformed manifest is simply skipped here; milestone 2's
        # validate_skill_package is responsible for reporting *why*.
        return None
    if not isinstance(data, dict):
        return None
    data["_dir"] = skill_dir.name
    return data


def scan() -> list[dict[str, Any]]:
    """Return raw manifests for every well-formed skill package, sorted by dir."""
    root = _skills_dir()
    if not root.is_dir():
        return []
    manifests: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        manifest = _load_manifest(child)
        if manifest is not None:
            manifests.append(manifest)
    return manifests


def _catalog_entry(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": manifest.get("id"),
        "name": manifest.get("name"),
        "version": manifest.get("version"),
        "summary": manifest.get("summary"),
        "capabilities": manifest.get("capabilities", []),
        "tags": manifest.get("tags", []),
        "risk_level": manifest.get("risk_level"),
        "platforms": manifest.get("platforms", []),
        "status": manifest.get("status", "draft"),
        "trust": skill_trust(manifest.get("id")),
    }


def list_skills(status: str | None = None) -> list[dict[str, Any]]:
    entries = [_catalog_entry(m) for m in scan()]
    if status is not None:
        entries = [e for e in entries if e["status"] == status]
    return entries


def catalog(with_validation: bool = False) -> list[dict[str, Any]]:
    """Catalog entries, optionally augmented with each package's validation status.

    The唯一 fact source remains each package manifest; validation is a derived view.
    """
    entries: list[dict[str, Any]] = []
    for manifest in scan():
        entry = _catalog_entry(manifest)
        if with_validation:
            # Lazy import avoids a circular import (validate imports registry).
            from .validate import validate_package_dir

            report = validate_package_dir(find_repo_root() / "skills" / manifest["_dir"])
            entry["validation"] = {
                "valid": report["valid"],
                "error_count": len(report["errors"]),
                "warn_count": len(report["warnings"]),
            }
        entries.append(entry)
    return entries


def search_skills(query: str, tags: list[str] | None = None) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    wanted_tags = {t.lower() for t in (tags or [])}
    results: list[dict[str, Any]] = []
    for entry in list_skills():
        haystack = " ".join(
            str(x)
            for x in (
                entry["id"],
                entry["name"],
                entry["summary"],
                " ".join(entry.get("capabilities") or []),
                " ".join(entry.get("tags") or []),
            )
        ).lower()
        if q and q not in haystack:
            continue
        if wanted_tags and not wanted_tags.issubset({t.lower() for t in (entry.get("tags") or [])}):
            continue
        results.append(entry)
    return results


# --- Domain system directory ------------------------------------------------

def _domains_dir() -> Path:
    return find_repo_root() / "domains"


def scan_domains() -> list[dict[str, Any]]:
    root = _domains_dir()
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for f in sorted(root.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict):
            data["_file"] = f.name
            out.append(data)
    return out


def _load_trust() -> dict[str, Any]:
    f = find_repo_root() / "registry" / "trust.yaml"
    if not f.is_file():
        return {}
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def domain_trust(domain_id: str | None) -> str:
    return ((_load_trust().get("domains") or {}).get(domain_id)) or "unverified"


def skill_trust(skill_id: str | None) -> str:
    return ((_load_trust().get("skills") or {}).get(skill_id)) or "unverified"


def _how_to_enter(reg: dict[str, Any]) -> dict[str, Any]:
    read_first = [reg.get("entry_resource")] + list(reg.get("also_read") or [])
    return {
        "mcp_endpoint": reg.get("mcp_endpoint"),
        "transport": reg.get("transport"),
        "read_first": [r for r in read_first if r],
    }


def _domain_entry(reg: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": reg.get("id"),
        "name": reg.get("name"),
        "domain": reg.get("domain"),
        "summary": reg.get("summary"),
        "teaches": reg.get("teaches", []),
        "keywords": reg.get("keywords", []),
        "safety_level": reg.get("safety_level"),
        "status": reg.get("status", "active"),
        "trust": domain_trust(reg.get("id")),
    }


def domain_catalog(with_validation: bool = False) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for reg in scan_domains():
        entry = _domain_entry(reg)
        if with_validation:
            from .validate import validate_domain_file

            report = validate_domain_file(_domains_dir() / reg["_file"])
            entry["validation"] = {
                "valid": report["valid"],
                "error_count": len(report["errors"]),
                "warn_count": len(report["warnings"]),
            }
        entries.append(entry)
    return entries


def get_domain_detail(domain_id: str) -> dict[str, Any] | None:
    known_skills = {s["id"] for s in list_skills()}
    for reg in scan_domains():
        if reg.get("id") == domain_id:
            public = {k: v for k, v in reg.items() if not k.startswith("_")}
            return {
                "registration": public,
                "trust": domain_trust(domain_id),
                "how_to_enter": _how_to_enter(reg),
                "requires_general_skills": [
                    {"skill_id": s, "available": s in known_skills}
                    for s in (reg.get("requires_general_skills") or [])
                ],
                "user_approval_note": "连接此领域 MCP 端点前需用户批准（safety_level=%s）。" % reg.get("safety_level"),
            }
    return None


def _matched_terms(terms: list[Any], task_lower: str) -> list[str]:
    return [str(t) for t in terms if t and str(t).lower() in task_lower]


def recommend_learning_path(task: str) -> dict[str, Any]:
    """Dumb, declarative matching of a task to domain systems + general skills.

    Matching is plain substring containment against self-declared keywords/teaches
    (domains) and capabilities/tags/summary (skills). NO LLM, NO semantic routing:
    the platform returns candidates WITH evidence; the calling Agent decides.
    """
    task_lower = (task or "").lower()
    known_skills = {s["id"] for s in list_skills()}

    domain_candidates: list[dict[str, Any]] = []
    for reg in scan_domains():
        if reg.get("status", "active") == "draft":
            continue  # draft domains are not recommended (D-GOV-3)
        terms = list(reg.get("keywords") or []) + list(reg.get("teaches") or [])
        matched = _matched_terms(terms, task_lower)
        if not matched:
            continue
        domain_candidates.append(
            {
                "id": reg.get("id"),
                "name": reg.get("name"),
                "domain": reg.get("domain"),
                "why": "matched: " + ", ".join(matched),
                "matched_terms": matched,
                "score": len(matched),
                "trust": domain_trust(reg.get("id")),
                "safety_level": reg.get("safety_level"),
                "how_to_enter": _how_to_enter(reg),
                "requires_general_skills": [
                    {"skill_id": s, "available": s in known_skills}
                    for s in (reg.get("requires_general_skills") or [])
                ],
                "user_approval_note": "连接此领域 MCP 端点前需用户批准（可能触及生产数据）。",
            }
        )
    domain_candidates.sort(key=lambda c: c["score"], reverse=True)

    skill_candidates: list[dict[str, Any]] = []
    for s in list_skills():
        terms = [s["id"], s.get("summary")] + list(s.get("capabilities") or []) + list(s.get("tags") or [])
        matched = _matched_terms(terms, task_lower)
        if matched:
            skill_candidates.append(
                {
                    "skill_id": s["id"],
                    "why": "matched: " + ", ".join(matched),
                    "matched_terms": matched,
                    "score": len(matched),
                }
            )
    skill_candidates.sort(key=lambda c: c["score"], reverse=True)

    return {
        "task_echo": task,
        "domain_candidates": domain_candidates,
        "general_skill_candidates": skill_candidates,
        "notes": (
            "建议性结果，非裁决。连接新 MCP 端点、安装通用技能均需用户批准。"
            "匹配为关键词/标签的朴素包含，最终判断由你（Agent）做出。"
        ),
    }


def read_skill_resource(skill_id: str, doc: str) -> str:
    """Serve a course's guide file by its logical resource key (skill://<id>/<doc>).

    The mapping <doc> -> file comes from the manifest's `resources`. Paths are
    confined to the package dir (defense in depth, though the validator already
    forbids traversal)."""
    manifest, pkg = manifest_and_dir(skill_id)
    if manifest is None or pkg is None:
        raise FileNotFoundError(f"unknown skill: {skill_id}")
    rel = (manifest.get("resources") or {}).get(doc)
    if not rel:
        raise FileNotFoundError(f"unknown resource '{doc}' for skill '{skill_id}'")
    target = (pkg / rel).resolve()
    pkg_resolved = pkg.resolve()
    if target != pkg_resolved and pkg_resolved not in target.parents:
        raise FileNotFoundError("resource path escapes package")
    return target.read_text(encoding="utf-8")


def read_skill_asset(skill_id: str, rel_path: str) -> str:
    """Serve a course's asset file content (verify script, runner template, requirements)
    so a REMOTE agent can fetch it and run it locally. Text only; path confined to the
    package dir. Raises FileNotFoundError / ValueError on bad input."""
    manifest, pkg = manifest_and_dir(skill_id)
    if manifest is None or pkg is None:
        raise FileNotFoundError(f"unknown skill: {skill_id}")
    target = (pkg / rel_path).resolve()
    pkg_resolved = pkg.resolve()
    if target != pkg_resolved and pkg_resolved not in target.parents:
        raise FileNotFoundError("asset path escapes package")
    if not target.is_file():
        raise FileNotFoundError(f"asset not found: {rel_path}")
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("binary assets are not supported over get_skill_asset (text only)") from exc


def manifest_and_dir(skill_id: str) -> tuple[dict[str, Any] | None, Path | None]:
    """Return (manifest, package_dir) for a skill id, or (None, None)."""
    for manifest in scan():
        if manifest.get("id") == skill_id:
            return manifest, find_repo_root() / "skills" / manifest["_dir"]
    return None, None


def get_skill_detail(skill_id: str) -> dict[str, Any] | None:
    for manifest in scan():
        if manifest.get("id") == skill_id:
            resources = manifest.get("resources", {}) or {}
            resource_uris = [f"skill://{skill_id}/{key}" for key in resources]
            public_manifest = {k: v for k, v in manifest.items() if not k.startswith("_")}
            return {
                "manifest": public_manifest,
                "resource_uris": resource_uris,
                "tools_required": manifest.get("tools_required", []),
                "risk_level": manifest.get("risk_level"),
            }
    return None
