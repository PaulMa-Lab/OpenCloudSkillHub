"""Minimal reference: connect an agent to a REMOTE OpenCloudSkillHub over streamable-http.

Framework-agnostic reference (uses the MCP Python SDK). openclaw / hermes should mirror
this flow in their own MCP-client config — the three values any MCP client needs are
listed at the bottom of examples/openclaw-minimal.md.

It walks the learning loop up to "I have the plan + the verify script in hand". Actually
executing the install/verify happens on the AGENT's side, under user approval (model A):
the Hub never runs anything.

Usage:
    python examples/openclaw_connect.py http://<server-ip>:8848 [<token>]
If no token is given, it self-registers one via POST /register.
"""

from __future__ import annotations

import asyncio
import sys

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

BASE = (sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8848")
TOKEN = sys.argv[2] if len(sys.argv) > 2 else None


def _content(result):
    sc = result.structuredContent
    if isinstance(sc, dict) and set(sc.keys()) == {"result"}:
        return sc["result"]
    return sc


async def main() -> int:
    token = TOKEN
    if not token:
        token = httpx.post(f"{BASE}/register", json={"name": "openclaw"}, timeout=10).json()["token"]
        print(f"self-registered token: {token[:8]}...")

    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(f"{BASE}/mcp", headers=headers) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()

            # 0. ORIENT — read the rules first
            guide = await s.read_resource("system://guide")
            print("0. read system://guide:", len(guide.contents[0].text), "chars")

            # 1. DISPATCH / find the skill for the task
            rec = _content(await s.call_tool("recommend_learning_path", {"task": "从一张截图里提取文字"}))
            print("1. recommended skills:", [x["skill_id"] for x in rec["general_skill_candidates"]])

            # 2. READ the course guide
            og = await s.read_resource("skill://ocr/guide")
            print("2. read skill://ocr/guide:", len(og.contents[0].text), "chars")

            # 3. ASSESS fit — the agent reports its OWN environment (remote Hub can't probe it)
            fit = _content(await s.call_tool(
                "assess_environment",
                {"skill_id": "ocr", "env_report": {"os": "Windows", "python_version": "3.12.3"}},
            ))
            print("3. fit: platform_supported=", fit["platform_supported"], "python_ok=", fit["python_ok"])

            # 4. PLAN — self-contained (packages inlined), each step carries approval/risk/rollback
            plan = _content(await s.call_tool("generate_install_plan", {"skill_id": "ocr"}))
            print("4. plan steps:", [st["id"] for st in plan["steps"]])

            # 5. FETCH the verify script content to run LOCALLY (agent-side, with approval)
            asset = _content(await s.call_tool(
                "get_skill_asset", {"skill_id": "ocr", "rel_path": "assets/verify_ocr.py"}
            ))
            print("5. fetched assets/verify_ocr.py:", len(asset.get("content", "")), "chars")

            print("\nNEXT (agent side, with user approval): run the approved plan steps in your")
            print("own environment -> run the fetched verify script -> use the capability.")
            print("The Hub gave you knowledge + plan + script content; it executed nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
