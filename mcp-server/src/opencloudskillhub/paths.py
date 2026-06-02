"""Repo-root resolution and content reading.

The platform serves content (system/* and skills/*) that lives OUTSIDE the
server code, on disk. This module locates the repo root robustly so the server
works regardless of the current working directory.

Resolution order:
1. OCSH_HOME environment variable (explicit override), if set.
2. Walk up from this file looking for the repo markers (system/guide.md + docs/).
3. Fallback: assume the standard layout mcp-server/src/opencloudskillhub/.
"""

from __future__ import annotations

import os
from pathlib import Path


def find_repo_root() -> Path:
    env = os.environ.get("OCSH_HOME")
    if env:
        return Path(env).expanduser().resolve()

    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "system" / "guide.md").exists() and (parent / "docs").is_dir():
            return parent

    # Fallback: server.py -> opencloudskillhub -> src -> mcp-server -> <repo root>
    return here.parents[3]


def read_text(rel_path: str) -> str:
    """Read a UTF-8 text file relative to the repo root.

    Raises FileNotFoundError with a clear message if the content is missing,
    so a misconfigured deployment fails loudly rather than serving silence.
    """
    path = find_repo_root() / rel_path
    if not path.is_file():
        raise FileNotFoundError(
            f"OpenCloudSkillHub content not found: {rel_path} (looked under {find_repo_root()})"
        )
    return path.read_text(encoding="utf-8")
