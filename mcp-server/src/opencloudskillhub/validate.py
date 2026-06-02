"""validate_skill_package — the quality/safety gate for course packages.

Implements the contract in docs/skill-package-contract.md §3 (rule codes
R-STRUCT-*, R-REF-*, R-CONS-*, R-SAFE-*, R-GOV-*). Read-only: it inspects a
package directory and reports findings; it never modifies anything and needs no
approval.

This is generic and skill-agnostic (ADR-003): it validates the *shape and
safety contract* of any package, with zero knowledge of what the skill does.

CLI:
    python -m opencloudskillhub.validate <package_dir> [<package_dir> ...]
    ocsh-validate <package_dir>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .paths import find_repo_root

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
# tools_required tokens that imply at least medium risk (R-SAFE-1).
MEDIUM_TRIGGERS = {"file_write", "shell_optional", "shell_required", "network_outbound", "model_download"}
# Package dirs referenced from guide markdown that we check for existence (R-CONS-1).
_GUIDE_REF_RE = re.compile(r"(?<![\w./-])((?:assets|requirements)/[\w./-]+\.\w+)")
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _finding(code: str, severity: str, message: str, *, field: str | None = None, path: str | None = None) -> dict[str, Any]:
    f: dict[str, Any] = {"code": code, "severity": severity, "message": message}
    if field is not None:
        f["field"] = field
    if path is not None:
        f["path"] = path
    return f


def _load_schema() -> dict[str, Any]:
    return json.loads((find_repo_root() / "registry" / "skill.schema.json").read_text(encoding="utf-8"))


def _classify_schema_error(err: Any) -> tuple[str, str]:
    path = list(err.absolute_path)
    top = path[0] if path else None
    v = err.validator
    if v == "required":
        return ("R-STRUCT-6", "error") if top == "resources" else ("R-STRUCT-2", "error")
    if v == "pattern":
        return ("R-STRUCT-3", "error") if top in ("id", "version") else ("R-STRUCT-2", "error")
    if v == "enum":
        if top == "tools_required":
            return ("R-STRUCT-5", "error")
        if top == "schema_version":
            return ("R-STRUCT-3", "error")
        return ("R-STRUCT-4", "error")
    if top == "resources":
        return ("R-STRUCT-6", "error")
    return ("R-STRUCT-2", "error")


def _is_traversal(rel: str) -> bool:
    if not rel or rel.startswith("/") or rel.startswith("\\"):
        return True
    p = Path(rel)
    if p.is_absolute() or (len(rel) >= 2 and rel[1] == ":"):
        return True
    return ".." in p.parts


def _declared_paths(manifest: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (field_label, rel_path) for every package-relative path the manifest references."""
    out: list[tuple[str, str]] = []
    resources = manifest.get("resources")
    if isinstance(resources, dict):
        for key, val in resources.items():
            if isinstance(val, str):
                out.append((f"resources.{key}", val))
    for single in ("troubleshooting", "diagnostics", "recipes", "safety"):
        val = manifest.get(single)
        if isinstance(val, str):
            out.append((single, val))
    install = manifest.get("install")
    if isinstance(install, dict):
        for plat, ref in install.items():
            if isinstance(ref, dict) and isinstance(ref.get("guide"), str):
                out.append((f"install.{plat}.guide", ref["guide"]))
    verification = manifest.get("verification")
    if isinstance(verification, dict):
        for key in ("smoke_test", "plan"):
            if isinstance(verification.get(key), str):
                out.append((f"verification.{key}", verification[key]))
    for i, prof in enumerate(manifest.get("install_profiles", []) or []):
        if isinstance(prof, dict):
            for req in prof.get("requirements", []) or []:
                if isinstance(req, str):
                    out.append((f"install_profiles[{i}].requirements", req))
    return out


def _semver_key(version: str) -> tuple[int, int, int] | None:
    m = _SEMVER_RE.match(version or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def validate_package_dir(package_dir: Path) -> dict[str, Any]:
    package_dir = Path(package_dir)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def add(f: dict[str, Any]) -> None:
        (errors if f["severity"] == "error" else warnings).append(f)

    manifest_file = package_dir / "skill.yaml"

    # R-STRUCT-1: parses as a YAML mapping.
    if not manifest_file.is_file():
        return _report(None, [_finding("R-STRUCT-1", "error", "skill.yaml not found", path="skill.yaml")], [])
    try:
        manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return _report(None, [_finding("R-STRUCT-1", "error", f"skill.yaml is not valid YAML: {exc}", path="skill.yaml")], [])
    if not isinstance(manifest, dict):
        return _report(None, [_finding("R-STRUCT-1", "error", "skill.yaml top level must be a mapping", path="skill.yaml")], [])

    skill_id = manifest.get("id")

    # R-STRUCT-2..6: JSON Schema structural validation.
    schema = _load_schema()
    for err in sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda e: list(e.absolute_path)):
        code, sev = _classify_schema_error(err)
        field = "/".join(str(p) for p in err.absolute_path) or None
        add(_finding(code, sev, err.message, field=field))

    # R-REF-1/2/3: filesystem existence + traversal guard.
    for field, rel in _declared_paths(manifest):
        if _is_traversal(rel):
            add(_finding("R-REF-2", "error", f"path escapes package or is absolute: {rel}", field=field, path=rel))
            continue
        target = package_dir / rel
        if not target.exists():
            add(_finding("R-REF-1", "error", f"referenced file not found: {rel}", field=field, path=rel))
        elif field == "verification.smoke_test" and not target.is_file():
            add(_finding("R-REF-3", "error", f"verification.smoke_test must be a file: {rel}", field=field, path=rel))

    # R-REF-4: internal reference resolution (install.<plat>.default_profile -> install_profiles id).
    profile_ids = {p.get("id") for p in (manifest.get("install_profiles") or []) if isinstance(p, dict)}
    install = manifest.get("install")
    if isinstance(install, dict):
        for plat, ref in install.items():
            if isinstance(ref, dict):
                dp = ref.get("default_profile")
                if dp is not None and dp not in profile_ids:
                    add(_finding("R-REF-4", "error", f"install.{plat}.default_profile '{dp}' has no matching install_profiles id", field=f"install.{plat}.default_profile"))

    # R-CONS-2: empty tags hurt discoverability (capabilities emptiness is a schema error).
    if not (manifest.get("tags") or []):
        add(_finding("R-CONS-2", "warn", "empty tags hurt discoverability", field="tags"))
    # R-CONS-3: summary length (warn, not a hard structural failure).
    summary = manifest.get("summary")
    if isinstance(summary, str) and len(summary) > 140:
        add(_finding("R-CONS-3", "warn", f"summary is {len(summary)} chars (>140 recommended max)", field="summary"))
    # R-CONS-5: profile platforms must be a subset of top-level platforms.
    top_platforms = set(manifest.get("platforms") or [])
    for i, prof in enumerate(manifest.get("install_profiles") or []):
        if isinstance(prof, dict):
            extra = set(prof.get("platforms") or []) - top_platforms
            if extra:
                add(_finding("R-CONS-5", "warn", f"profile platforms {sorted(extra)} not in top-level platforms", field=f"install_profiles[{i}].platforms"))
    # R-CONS-1: guide markdown references to package dirs should exist (best-effort).
    _check_guide_refs(package_dir, manifest, add)

    # R-SAFE-1: declared risk_level must meet the floor implied by tools_required.
    tools = set(manifest.get("tools_required") or [])
    risk = manifest.get("risk_level")
    if risk in RISK_ORDER:
        floor = "medium" if tools & MEDIUM_TRIGGERS else "low"
        if RISK_ORDER[risk] < RISK_ORDER[floor]:
            add(_finding("R-SAFE-1", "error", f"risk_level '{risk}' below floor '{floor}' implied by tools_required {sorted(tools & MEDIUM_TRIGGERS)}", field="risk_level"))
        elif "shell_required" in tools and (tools & {"network_outbound", "model_download"}) and risk != "high":
            add(_finding("R-SAFE-1", "warn", "shell_required + network/model download suggests risk_level: high", field="risk_level"))

    # R-SAFE-2: download implies declared network access.
    downloads = "model_download" in tools or any(
        isinstance(p, dict) and (p.get("est_download_mb") or 0) > 0 for p in (manifest.get("install_profiles") or [])
    )
    if downloads and "network_outbound" not in tools:
        add(_finding("R-SAFE-2", "error", "downloads (model_download / est_download_mb>0) require network_outbound in tools_required", field="tools_required"))

    # R-GOV-1: trust must not be self-declared.
    if "trust" in manifest:
        add(_finding("R-GOV-1", "error", "trust must not be self-declared; it is assigned in registry/trust.yaml", field="trust"))
    # R-GOV-2: version must not regress vs another package with the same id.
    _check_version_monotonic(package_dir, manifest, add)
    # R-GOV-3: draft status is indexed but flagged.
    if manifest.get("status", "draft") == "draft":
        add(_finding("R-GOV-3", "warn", "status is draft; will be flagged and excluded from recommendations", field="status"))

    return _report(skill_id, errors, warnings)


def _check_guide_refs(package_dir: Path, manifest: dict[str, Any], add: Any) -> None:
    seen: set[str] = set()
    for field, rel in _declared_paths(manifest):
        if not field.startswith("resources.") and field != "safety" and not field.startswith("install."):
            continue
        if not rel.endswith(".md"):
            continue
        md = package_dir / rel
        if not md.is_file():
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _GUIDE_REF_RE.findall(text):
            if match in seen:
                continue
            seen.add(match)
            if _is_traversal(match):
                continue
            if not (package_dir / match).exists():
                add(_finding("R-CONS-1", "warn", f"guide references missing package file: {match}", field=rel, path=match))


def _check_version_monotonic(package_dir: Path, manifest: dict[str, Any], add: Any) -> None:
    sid, ver = manifest.get("id"), manifest.get("version")
    key = _semver_key(ver) if isinstance(ver, str) else None
    if not sid or key is None:
        return
    skills_root = package_dir.parent
    for sibling in skills_root.iterdir() if skills_root.is_dir() else []:
        if not sibling.is_dir() or sibling == package_dir:
            continue
        sm = sibling / "skill.yaml"
        if not sm.is_file():
            continue
        try:
            other = yaml.safe_load(sm.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(other, dict) and other.get("id") == sid:
            okey = _semver_key(other.get("version", ""))
            if okey and key < okey:
                add(_finding("R-GOV-2", "error", f"version {ver} regresses below existing {other.get('version')} for id '{sid}'", field="version"))


def _report(skill_id: str | None, errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "skill_id": skill_id,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": f"{len(errors)} error(s), {len(warnings)} warning(s)",
    }


def _load_domain_schema() -> dict[str, Any]:
    return json.loads((find_repo_root() / "registry" / "domain.schema.json").read_text(encoding="utf-8"))


def _classify_domain_error(err: Any) -> tuple[str, str]:
    path = list(err.absolute_path)
    top = path[0] if path else None
    v = err.validator
    if v == "required":
        return ("D-STRUCT-2", "error")
    if v == "pattern":
        return ("D-STRUCT-3", "error") if top == "id" else ("D-STRUCT-2", "error")
    if v == "enum":
        if top == "schema_version":
            return ("D-STRUCT-3", "error")
        if top in ("safety_level", "status", "transport"):
            return ("D-STRUCT-4", "error")
        return ("D-STRUCT-4", "error")
    return ("D-STRUCT-2", "error")


def validate_domain_file(path: Path) -> dict[str, Any]:
    """Validate a domain registration file against the domain contract
    (docs/domain-registration-contract.md). Read-only."""
    path = Path(path)
    if not path.is_file():
        return _report(None, [_finding("D-STRUCT-1", "error", "domain file not found", path=path.name)], [])
    try:
        reg = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return _report(None, [_finding("D-STRUCT-1", "error", f"not valid YAML: {exc}", path=path.name)], [])
    if not isinstance(reg, dict):
        return _report(None, [_finding("D-STRUCT-1", "error", "top level must be a mapping", path=path.name)], [])

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def add(f: dict[str, Any]) -> None:
        (errors if f["severity"] == "error" else warnings).append(f)

    domain_id = reg.get("id")

    schema = _load_domain_schema()
    for err in sorted(Draft202012Validator(schema).iter_errors(reg), key=lambda e: list(e.absolute_path)):
        code, sev = _classify_domain_error(err)
        add(_finding(code, sev, err.message, field="/".join(str(p) for p in err.absolute_path) or None))

    # D-SAFE-1: endpoint must be https.
    endpoint = reg.get("mcp_endpoint")
    if isinstance(endpoint, str) and not endpoint.lower().startswith("https://"):
        add(_finding("D-SAFE-1", "error", f"mcp_endpoint must be https: {endpoint}", field="mcp_endpoint"))

    # D-REF-1: required general skills should resolve in the skills catalog (warn — may be added later).
    from . import registry

    known = {s["id"] for s in registry.list_skills()}
    for sid in reg.get("requires_general_skills") or []:
        if sid not in known:
            add(_finding("D-REF-1", "warn", f"requires_general_skills '{sid}' not found in skills catalog (may be added later)", field="requires_general_skills"))

    # D-GOV-1: trust must not be self-declared.
    if "trust" in reg:
        add(_finding("D-GOV-1", "error", "trust must not be self-declared; it is assigned in registry/trust.yaml", field="trust"))
    # D-GOV-3: draft is indexed but flagged.
    if reg.get("status", "active") == "draft":
        add(_finding("D-GOV-3", "warn", "status is draft; will be flagged and excluded from recommendations", field="status"))

    return _report(domain_id, errors, warnings)


def validate_domain_id(domain_id: str) -> dict[str, Any] | None:
    domains_dir = find_repo_root() / "domains"
    if domains_dir.is_dir():
        for f in sorted(domains_dir.glob("*.yaml")):
            try:
                reg = yaml.safe_load(f.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                reg = None
            if isinstance(reg, dict) and reg.get("id") == domain_id:
                return validate_domain_file(f)
    return None


def validate_skill_id(skill_id: str) -> dict[str, Any] | None:
    """Resolve a skill id under skills/ and validate it. None if id is unknown."""
    skills_dir = find_repo_root() / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            if (child / "skill.yaml").is_file():
                try:
                    m = yaml.safe_load((child / "skill.yaml").read_text(encoding="utf-8"))
                except yaml.YAMLError:
                    m = None
                if isinstance(m, dict) and m.get("id") == skill_id:
                    return validate_package_dir(child)
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: ocsh-validate <package_dir> [<package_dir> ...]", file=sys.stderr)
        return 2
    worst = 0
    for arg in args:
        report = validate_package_dir(Path(arg))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        worst = max(worst, 0 if report["valid"] else 1)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
