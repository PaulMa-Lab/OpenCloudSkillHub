"""Milestone-1 MCP smoke test: spawn the server over stdio and drive it as a client.

Proves the server completes the MCP initialize handshake and that resources/tools
are actually listable/callable over the wire (not just importable).

Usage (from the venv):
    python scripts/mcp_smoke.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parents[1]


async def run() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "opencloudskillhub.server"],
        env={"OCSH_HOME": str(REPO_ROOT)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"initialized: server = {init.serverInfo.name}")
            if init.instructions:
                print(f"instructions: {init.instructions[:70]!r}...")

            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])

            resources = await session.list_resources()
            print("resources:", [str(r.uri) for r in resources.resources])

            guide = await session.read_resource("system://guide")
            text = guide.contents[0].text if guide.contents else ""
            print(f"read system://guide -> {len(text)} chars, starts: {text[:40]!r}")

            result = await session.call_tool("list_skills", {})
            print("call list_skills ->", result.structuredContent)

            domains = await session.read_resource("domains://catalog")
            dtext = domains.contents[0].text if domains.contents else ""
            print(f"read domains://catalog -> {len(dtext)} chars")

            rec = await session.call_tool(
                "recommend_learning_path", {"task": "帮用户招聘一个电商运营"}
            )
            sc = rec.structuredContent or {}
            cands = sc.get("domain_candidates", [])
            print("recommend_learning_path -> domain candidates:", [c["id"] for c in cands])
            if cands:
                print("  how_to_enter:", cands[0]["how_to_enter"]["mcp_endpoint"], "| trust:", cands[0]["trust"])

    print("MCP SMOKE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
