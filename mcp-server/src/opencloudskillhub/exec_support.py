"""Generic, skill-agnostic execution-support tools (milestone 5).

These are the platform's read-only / pure-computation helpers that let an agent
install, verify, and troubleshoot ANY course — parameterized by skill_id, driven
entirely by the course's manifest + assets. There is NO skill-specific logic here
(ADR-003), and the platform NEVER executes install/verify steps (ADR-001 model A):
generate_install_plan returns a plan, get_verification_plan returns a command, and
the HOST runs them under user approval.

Install policy (platform-level, skill-agnostic):
  - one isolated venv per skill at  ~/.opencloudskillhub/envs/<skill_id>
  - Python 3.12 (pinned platform default)
  - rollback == delete the venv dir
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from . import registry


def _env_dir(skill_id: str) -> Path:
    return Path.home() / ".opencloudskillhub" / "envs" / skill_id


def _venv_python(skill_id: str) -> str:
    return str(_env_dir(skill_id) / "Scripts" / "python.exe")


# --- detect_environment -----------------------------------------------------

def _list_pythons() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    try:
        result = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return out
    for line in result.stdout.splitlines():
        ver = re.search(r"-V:(\S+)", line)
        path = re.search(r"([A-Za-z]:\\[^\r\n*]+\.exe)", line)
        if ver and path:
            out.append({"version": ver.group(1), "path": path.group(1).strip()})
    return out


def _disk_free_mb() -> int | None:
    try:
        return shutil.disk_usage(Path.home()).free // (1024 * 1024)
    except OSError:
        return None


def detect_environment(skill_id: str | None = None) -> dict[str, Any]:
    info: dict[str, Any] = {
        "os": platform.system(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "python_running": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "in_venv": sys.prefix != sys.base_prefix,
        },
        "available_pythons": _list_pythons(),
        "disk_free_mb": _disk_free_mb(),
        "gpu": "unknown",
        "note": (
            "反映运行本 Hub 的机器（stdio/本地部署下即用户机器）。"
            "未主动探测网络可达性以避免副作用。"
        ),
    }
    if skill_id:
        manifest, _ = registry.manifest_and_dir(skill_id)
        if manifest is None:
            info["skill_fit"] = {"skill_id": skill_id, "error": "unknown skill"}
        else:
            os_token = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(platform.system())
            info["skill_fit"] = {
                "skill_id": skill_id,
                "platform_supported": os_token in (manifest.get("platforms") or []),
                "required_tools": manifest.get("tools_required", []),
                "profiles": [p.get("id") for p in (manifest.get("install_profiles") or [])],
                "recommended_python": "3.12",
            }
    return info


# --- generate_install_plan --------------------------------------------------

def generate_install_plan(skill_id: str, profile_id: str | None = None, platform_key: str = "windows") -> dict[str, Any]:
    manifest, pkg = registry.manifest_and_dir(skill_id)
    if manifest is None or pkg is None:
        return {"error": f"unknown skill: {skill_id}"}

    install = (manifest.get("install") or {}).get(platform_key, {})
    profiles = {p["id"]: p for p in (manifest.get("install_profiles") or []) if isinstance(p, dict) and "id" in p}
    pid = profile_id or install.get("default_profile") or (next(iter(profiles)) if profiles else None)
    if pid not in profiles:
        return {"error": f"unknown profile '{pid}' for skill {skill_id}", "available_profiles": list(profiles)}
    profile = profiles[pid]

    env_str = str(_env_dir(skill_id))
    vpy = _venv_python(skill_id)
    rollback = f'Remove-Item -Recurse -Force "{env_str}"'
    steps: list[dict[str, Any]] = []

    def add(step_id: str, intent: str, command: str, *, writes: str | None = None, risk: str = "medium", approval: bool = True, rb: str | None = None) -> None:
        steps.append({
            "id": step_id, "intent": intent, "command": command, "writes": writes,
            "risk": risk, "approval_required": approval, "rollback": rb,
        })

    if profile.get("creates_venv", True):
        add("create_venv", "创建独立 venv（Python 3.12），隔离安装", f'py -3.12 -m venv "{env_str}"', writes=env_str, risk="medium", rb=rollback)
        add("upgrade_pip", "升级 pip", f'"{vpy}" -m pip install -U pip', risk="low", rb=rollback)

    for req in profile.get("requirements", []) or []:
        req_abs = str(pkg / req)
        add("install_requirements", f"安装依赖（profile={pid}）", f'"{vpy}" -m pip install -r "{req_abs}"', risk=profile.get("risk_level", "medium"), rb=rollback)

    verification = manifest.get("verification") or {}
    smoke = verification.get("smoke_test")
    smoke_abs = str(pkg / smoke) if smoke else None
    if smoke_abs:
        add("smoke_test", "快速自检：import + 引擎初始化（不下大模型）", f'"{vpy}" "{smoke_abs}" --smoke', risk="low")

    est = profile.get("est_download_mb") or 0
    if est > 0 or "model_download" in (manifest.get("tools_required") or []):
        cmd = f'"{vpy}" "{smoke_abs}"' if smoke_abs else "(首次运行 runner 时自动下载)"
        add("download_model", f"首次完整运行会下载模型（约 {est}MB）", cmd, risk="medium")

    runner_tpl = pkg / "assets" / "runner_template.py"
    if runner_tpl.exists():
        runner_out = str(_env_dir(skill_id) / "ocr_runner.py")
        add("generate_runner", "生成可复用 runner（固化 venv + 引擎）", f'Copy-Item "{runner_tpl}" "{runner_out}"', writes=runner_out, risk="low", rb=rollback)

    return {
        "skill_id": skill_id,
        "profile_id": pid,
        "platform": platform_key,
        "env_path": env_str,
        "venv_python": vpy,
        "est_download_mb": profile.get("est_download_mb"),
        "steps": steps,
        "summary": f"{len(steps)} step(s); profile={pid}; 多数步骤需用户批准后由宿主执行。",
        "note": "平台只生成计划，不执行。每个 approval_required=true 的步骤由宿主在用户批准下执行（模型 A）。",
    }


# --- get_verification_plan --------------------------------------------------

def get_verification_plan(skill_id: str) -> dict[str, Any]:
    manifest, pkg = registry.manifest_and_dir(skill_id)
    if manifest is None or pkg is None:
        return {"error": f"unknown skill: {skill_id}"}
    verification = manifest.get("verification") or {}
    smoke = verification.get("smoke_test")
    if not smoke:
        return {"skill_id": skill_id, "error": "no verification declared"}
    vpy = _venv_python(skill_id)
    smoke_abs = str(pkg / smoke)
    return {
        "skill_id": skill_id,
        "smoke_test": smoke_abs,
        "smoke_command": f'"{vpy}" "{smoke_abs}" --smoke',
        "run_command": f'"{vpy}" "{smoke_abs}"',
        "expected": verification.get("expected"),
        "note": "由宿主在该 skill 的 venv 中执行，将实际输出与 expected 比对。平台不执行。",
    }


# --- diagnose_error ---------------------------------------------------------

def diagnose_error(skill_id: str, logs: str) -> dict[str, Any]:
    manifest, pkg = registry.manifest_and_dir(skill_id)
    if manifest is None or pkg is None:
        return {"error": f"unknown skill: {skill_id}"}
    logs_lower = (logs or "").lower()
    matched: list[dict[str, Any]] = []

    diag_path = manifest.get("diagnostics")
    if diag_path:
        try:
            data = yaml.safe_load((pkg / diag_path).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            data = {}
        for rule in data.get("rules", []) or []:
            keywords = [str(k).lower() for k in (rule.get("match") or [])]
            hits = [k for k in keywords if k in logs_lower]
            if hits:
                matched.append({
                    "id": rule.get("id"),
                    "cause": rule.get("cause"),
                    "actions": rule.get("actions", []),
                    "ref": rule.get("ref"),
                    "matched_keywords": hits,
                })

    has_ts = bool((manifest.get("resources") or {}).get("troubleshooting"))
    return {
        "skill_id": skill_id,
        "matched": matched,
        "troubleshooting_resource": f"skill://{skill_id}/troubleshooting" if has_ts else None,
        "note": (
            "命中以上排错规则；采取单一明确动作后回到验证。"
            if matched
            else "未命中已知规则；读完整 troubleshooting 资源，或用 submit_skill_feedback 回传。"
        ),
    }
