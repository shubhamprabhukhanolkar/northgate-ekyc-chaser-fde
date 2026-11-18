import asyncio
import contextlib
import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .db import initialize
from .worker import worker
from .mcp.server import mcp
from .mcp.readonly import readonly_mcp
from .mcp import oauth
from .llm.router import ProviderUnavailable
from .routes import auth_routes, cases_routes, prompts_routes, finops_routes, copilot_routes, live_routes
from . import live
from .routes import cfo_routes
from .routes import cro_routes

logging.basicConfig(level=logging.INFO, format='%(message)s')
mcp_app = mcp.streamable_http_app()
readonly_app = readonly_mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    initialize()
    live.recover_interrupted()
    task = asyncio.create_task(worker())
    try:
        async with mcp.session_manager.run():
            async with readonly_mcp.session_manager.run():
                yield
    finally:
        await live.shutdown()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Northgate eKYC", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.middleware("http")
async def protect(request: Request, call_next):
    path = request.url.path
    if path == "/mcp-readonly" or path.startswith("/mcp-readonly/"):
        authorization = request.headers.get("authorization", "")
        identity = oauth.verify_access(authorization[7:] if authorization.startswith("Bearer ") else "", oauth.resource_url(request))
        if not identity:
            metadata = oauth.origin(request) + "/.well-known/oauth-protected-resource/mcp-readonly"
            return JSONResponse({"detail": "Connect your Northgate account for read-only access"}, status_code=401,
                                headers={"WWW-Authenticate": f'Bearer resource_metadata="{metadata}", scope="{oauth.SCOPE}"', "Cache-Control": "no-store"})
        request.state.mcp_reader = identity
    if path == "/mcp" or path.startswith("/mcp/"):
        key = settings().mcp_api_key
        if not key or not secrets.compare_digest(request.headers.get("authorization", ""), f"Bearer {key}"):
            return JSONResponse({"detail": "MCP bearer key required"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
    # Browser mutations must originate from this host; bearer clients have no Origin.
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        return JSONResponse({"detail": "Cross-origin mutation blocked"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if path.startswith(("/api", "/mcp", "/oauth", "/.well-known/")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ProviderUnavailable)
async def provider_error(request, exc):
    logging.error(json.dumps({"event": "provider_unavailable", "detail": str(exc)}))
    return JSONResponse({"detail": str(exc)}, status_code=503)


@app.exception_handler(oauth.OAuthError)
async def oauth_error(request, exc):
    return JSONResponse({"error": exc.error, "error_description": exc.description}, status_code=exc.status,
                        headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


for router in (auth_routes.router, cases_routes.router, prompts_routes.router, finops_routes.router, copilot_routes.router, live_routes.router, oauth.router, cfo_routes.router, cro_routes.router):
    app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "northgate-ekyc", "synthetic": True, "offline_demo": settings().offline_demo}


app.mount("/mcp", mcp_app)
app.mount("/mcp-readonly", readonly_app)
static = Path(settings().static_dir)
if (static / "assets").exists():
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    if path.startswith(("api/", "mcp/")):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    if (static / "index.html").exists():
        return FileResponse(static / "index.html")
    return JSONResponse({"detail": "Build frontend first: cd frontend && npm ci && npm run build"}, status_code=503)
