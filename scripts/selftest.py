"""Milestone-1 self-test: verify the platform core loads and serves content.

Runs WITHOUT a full MCP client. Checks:
  1. repo-root resolution finds the content dirs,
  2. system resources are readable,
  3. the registry scans skills/ (empty is fine in milestone 1),
  4. the FastMCP server module imports (i.e., all resource/tool registration ran).

Usage (from the venv):
    python scripts/selftest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the src/ layout importable when run directly (without an editable install).
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "mcp-server" / "src"))


def main() -> int:
    from opencloudskillhub import registry
    from opencloudskillhub.paths import find_repo_root, read_text

    root = find_repo_root()
    print(f"repo root: {root}")

    for rel in ("system/guide.md", "system/curriculum.md", "system/changelog.md"):
        text = read_text(rel)
        assert text.strip(), f"{rel} is empty"
        print(f"  resource OK: {rel} ({len(text)} chars)")

    skills = registry.list_skills()
    print(f"  registry scan: {len(skills)} skill(s) -> {[s.get('id') for s in skills]}")

    # Importing the server module runs all @mcp.resource / @mcp.tool registration.
    from opencloudskillhub import server  # noqa: F401

    print("  server module imported OK (resources + tools registered)")
    print("SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
