"""HTTP serve mode (ADR-005): streamable-http + lightweight bearer token + self-register.

Test-phase posture (user decision 2026-06-02): invite-only testing, security
deliberately light — plain HTTP on a public IP is acceptable for now; the token is an
identity / self-registration handle, NOT a hardened boundary. TLS/domain hardening is
deferred. The real security priority is course supply-chain (ADR-004), not network
attacks. The Hub still never executes anything (model A): it only serves knowledge.

Endpoints:
  POST /register {name?}      -> {token}   (public; self-service)
  GET  /healthz               -> {ok}
  *    /mcp                    -> MCP streamable-http (requires Bearer token unless OCSH_AUTH=off)

Env knobs:
  OCSH_HOST (default 0.0.0.0), OCSH_PORT (default 8848)
  OCSH_AUTH=off            -> disable token check (open)
  OCSH_ADMIN_TOKEN=<tok>   -> a static always-valid token for ops
  OCSH_TOKENS_FILE=<path>  -> token store (default registry/tokens.json, gitignored)
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .paths import find_repo_root
from .server import mcp


def _tokens_path() -> Path:
    override = os.environ.get("OCSH_TOKENS_FILE")
    return Path(override) if override else find_repo_root() / "registry" / "tokens.json"


def _load() -> dict:
    p = _tokens_path()
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"tokens": {}, "revoked": []}


def _save(data: dict) -> None:
    p = _tokens_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _auth_enabled() -> bool:
    return os.environ.get("OCSH_AUTH", "on").lower() != "off"


def _valid(token: str) -> bool:
    if not token:
        return False
    admin = os.environ.get("OCSH_ADMIN_TOKEN")
    if admin and token == admin:
        return True
    data = _load()
    h = _hash(token)
    return h in data.get("tokens", {}) and h not in data.get("revoked", [])


async def register(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 — tolerate empty/invalid body
        body = {}
    name = (body or {}).get("name") or "anonymous"
    token = secrets.token_urlsafe(24)
    data = _load()
    data.setdefault("tokens", {})[_hash(token)] = {
        "name": str(name)[:80],
        "created": datetime.now(timezone.utc).isoformat(),
    }
    _save(data)
    return JSONResponse(
        {
            "token": token,
            "name": name,
            "usage": "Connect MCP client to /mcp with header  Authorization: Bearer <token>",
            "note": "测试期明文 HTTP；token 是身份标识不是安全边界。执行仍在你侧、需你侧批准（模型 A）。",
        }
    )


async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "auth": _auth_enabled()})


class _AuthASGI:
    """Pure-ASGI bearer-token gate (avoids buffering streamable-http responses).

    Lets /register and /healthz through, and passes non-HTTP scopes (lifespan) straight
    to the inner app so the MCP session manager starts normally.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not _auth_enabled():
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if path in ("/register", "/healthz"):
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in (scope.get("headers") or [])}
        auth = headers.get("authorization", "")
        token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        if _valid(token):
            return await self.app(scope, receive, send)
        resp = JSONResponse(
            {"error": "unauthorized", "hint": "POST /register to get a token, then send Authorization: Bearer <token>"},
            status_code=401,
        )
        return await resp(scope, receive, send)


def build_app():
    app = mcp.streamable_http_app()  # Starlette app serving MCP at /mcp (+ its lifespan)
    app.router.routes.append(Route("/register", register, methods=["POST"]))
    app.router.routes.append(Route("/healthz", healthz, methods=["GET"]))
    return _AuthASGI(app)


def serve() -> None:
    import uvicorn

    host = os.environ.get("OCSH_HOST", "0.0.0.0")
    port = int(os.environ.get("OCSH_PORT", "8848"))
    uvicorn.run(build_app(), host=host, port=port, log_level=os.environ.get("OCSH_LOG", "info"))
