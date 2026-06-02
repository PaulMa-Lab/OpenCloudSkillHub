"""End-to-end walkthrough (milestone 7): drive the Hub through the full loop.

This is a SCRIPTED client (not a real LLM agent) that performs, in order, the steps
the curriculum tells an agent to take. It proves the loop is mechanically complete
end-to-end over MCP, and produces a readable transcript (examples/transcript.md).

What it does NOT prove: that a real LLM agent will *choose* to follow this order on
its own — that is the genuine open question, testable only by connecting a real
Claude Code agent (see mcp-server/README.md for .mcp.json).

Run from the venv:
    python examples/e2e_ocr_learning.py
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parents[1]
OCR_VENV_PY = Path.home() / ".opencloudskillhub" / "envs" / "ocr" / "Scripts" / "python.exe"


def _h(title: str) -> None:
    print("\n" + "=" * 78 + f"\n# {title}\n" + "=" * 78)


def _content(result):
    sc = result.structuredContent
    if isinstance(sc, dict) and set(sc.keys()) == {"result"}:
        return sc["result"]
    return sc


async def run() -> int:
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "opencloudskillhub.server"], env={"OCSH_HOME": str(REPO_ROOT)}
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()

            _h("0. ORIENT — read system://guide (instructions delivered at handshake)")
            print("server:", init.serverInfo.name)
            print("instructions[:160]:", (init.instructions or "")[:160], "...")
            guide = await session.read_resource("system://guide")
            print(f"system://guide -> {len(guide.contents[0].text)} chars read")

            _h("1a. DISPATCH a DOMAIN task — recommend_learning_path")
            dom = _content(await session.call_tool("recommend_learning_path", {"task": "帮用户招聘一个电商运营"}))
            for c in dom["domain_candidates"]:
                print(f"  -> domain '{c['id']}' ({c['why']}) trust={c['trust']} safety={c['safety_level']}")
                print(f"     enter: {c['how_to_enter']['mcp_endpoint']}  read_first={c['how_to_enter']['read_first']}")
                print(f"     needs general skills: {[s['skill_id'] + ('' if s['available'] else '(unavailable)') for s in c['requires_general_skills']]}")
                print(f"     {c['user_approval_note']}")

            _h("1b. DISPATCH a GENERAL-SKILL task — recommend_learning_path")
            gen = _content(await session.call_tool("recommend_learning_path", {"task": "我需要从一张截图里提取文字"}))
            print("  domain candidates:", [c["id"] for c in gen["domain_candidates"]])
            print("  general skill candidates:", [(s["skill_id"], s["why"]) for s in gen["general_skill_candidates"]])

            _h("2. SELECT the OCR course — get_skill_detail")
            detail = _content(await session.call_tool("get_skill_detail", {"skill_id": "ocr"}))
            print("  trust:", detail["manifest"].get("status"), "| risk:", detail["risk_level"])
            print("  required host tools:", detail["tools_required"])
            print("  resource URIs:", detail["resource_uris"])

            _h("3. READ the course guide — skill://ocr/guide (resource template)")
            ocr_guide = await session.read_resource("skill://ocr/guide")
            print(ocr_guide.contents[0].text.split("\n\n")[1])  # the "何时该用" gist

            _h("4. ASSESS fit — detect_environment('ocr')")
            env = _content(await session.call_tool("detect_environment", {"skill_id": "ocr"}))
            print("  os:", env["os"], env["arch"], "| disk_free_mb:", env["disk_free_mb"])
            print("  pythons:", [p["version"] for p in env["available_pythons"]])
            print("  skill_fit:", env["skill_fit"])

            _h("5. PLAN — generate_install_plan('ocr')  (Hub plans; HOST executes)")
            plan = _content(await session.call_tool("generate_install_plan", {"skill_id": "ocr"}))
            print(f"  profile={plan['profile_id']}  env={plan['env_path']}  est_download_mb={plan['est_download_mb']}")
            for s in plan["steps"]:
                gate = "APPROVAL" if s["approval_required"] else "auto"
                print(f"    [{gate}/{s['risk']}] {s['id']}: {s['command']}")

            _h("6. VERIFY — get_verification_plan('ocr') then HOST runs it")
            vp = _content(await session.call_tool("get_verification_plan", {"skill_id": "ocr"}))
            print("  expected:", vp["expected"])
            print("  run_command:", vp["run_command"])
            if OCR_VENV_PY.is_file():
                proc = subprocess.run([str(OCR_VENV_PY), vp["smoke_test"]], capture_output=True, text=True, timeout=180)
                print("  --- HOST executed verify (real) ---")
                print("  " + proc.stdout.strip().replace("\n", "\n  "))
                print("  exit code:", proc.returncode)
            else:
                print("  (OCR venv not installed; skipping real execution — run the install plan first)")

            _h("7. (failure path) DIAGNOSE — diagnose_error('ocr', logs)")
            fake = "ImportError: A module compiled using NumPy 1.x cannot be run in NumPy 2.x; _ARRAY_API not found"
            diag = _content(await session.call_tool("diagnose_error", {"skill_id": "ocr", "logs": fake}))
            for m in diag["matched"]:
                print(f"  -> {m['id']}: {m['cause']}  actions={m['actions']}")

            _h("8. FEEDBACK — submit_skill_feedback")
            fb = _content(await session.call_tool("submit_skill_feedback", {"skill_id": "ocr", "outcome": "verified"}))
            print("  accepted:", fb["accepted"], "| id:", fb["id"])

    print("\nE2E COMPLETE — the full loop is mechanically connected over MCP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
