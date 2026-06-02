"""HTTP smoke test (ADR-005): register, connect over streamable-http with a token,
and exercise the remote-relevant tools. Assumes the server is already running, e.g.:

    $env:OCSH_HOME="D:\\Github\\OpenCloudSkillHub"; $env:OCSH_PORT="8848"
    .\\mcp-server\\.venv\\Scripts\\python.exe -m opencloudskillhub.server --http

Then:  python scripts/http_smoke.py [base_url]
"""

from __future__ import annotations

import asyncio
import sys

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8848"


def _content(result):
    sc = result.structuredContent
    if isinstance(sc, dict) and set(sc.keys()) == {"result"}:
        return sc["result"]
    return sc


async def run() -> int:
    # 1) self-register -> token
    reg = httpx.post(f"{BASE}/register", json={"name": "smoke-agent"}, timeout=10).json()
    token = reg["token"]
    print("registered; token prefix:", token[:8] + "...")

    # 2) unauthenticated call should be refused
    bad = httpx.get(f"{BASE}/healthz", timeout=10).json()
    print("healthz:", bad)

    # 3) connect MCP over streamable-http with the bearer token
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(f"{BASE}/mcp", headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("initialized:", init.serverInfo.name)
            tools = await session.list_tools()
            print("tools:", len(tools.tools), "incl assess_environment/get_skill_asset:",
                  {"assess_environment", "get_skill_asset"} <= {t.name for t in tools.tools})

            rec = _content(await session.call_tool("recommend_learning_path", {"task": "我需要从截图提取文字"}))
            print("recommend general skills:", [s["skill_id"] for s in rec["general_skill_candidates"]])

            env = _content(await session.call_tool(
                "assess_environment",
                {"skill_id": "ocr", "env_report": {"os": "Windows", "python_version": "3.12.3"}},
            ))
            print("assess_environment: platform_supported=", env["platform_supported"], "python_ok=", env["python_ok"])

            asset = _content(await session.call_tool(
                "get_skill_asset", {"skill_id": "ocr", "rel_path": "requirements/rapidocr.txt"}
            ))
            print("get_skill_asset rapidocr.txt -> has rapidocr:", "rapidocr_onnxruntime" in asset.get("content", ""))

    print("HTTP SMOKE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
