import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from keel.config import settings
from keel.errors import KeelError

from keel.routes.library import router as library_router
from keel.store import get_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("keel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the catalog from `catalog/*.yaml` into memory on startup — no setup step."""
    store = get_store()
    logger.info(
        "Loaded catalog: %d threats, %d mitigations", len(store.threats), len(store.mitigations)
    )
    yield


app = FastAPI(
    title="Keel",
    description="Read-only browse API for the Keel threat model. Writes go through MCP.",
    version="0.1.0",
    lifespan=lifespan,
)

# No CORS headers, on purpose. The UI is served by this app, so it is same-origin and
# needs none. This used to allow every origin, which let any page open in the user's
# browser read the catalog and the assessment reports and write to both: the server
# listened on loopback and was reachable from the whole web through the browser.
# Without the headers the browser refuses such a page the answer.
#
# A write is refused here rather than left to the browser. A browser says where a
# request came from in `Origin`, and a page cannot forge it, so a write that names an
# origin other than this app is turned away before it reaches a route. A request with no
# `Origin` did not come from a page - it is a script or a test - and is let through.


@app.middleware("http")
async def refuse_writes_from_other_sites(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and request.method not in ("GET", "HEAD", "OPTIONS"):
        if urlsplit(origin).hostname not in settings.allowed_hosts:
            return JSONResponse(
                status_code=403,
                content={"error": "this request came from another site", "success": False},
            )
    return await call_next(request)


# The host check closes what is left: a page that points its own name at 127.0.0.1 is
# same-origin as far as the browser can tell, but it has to ask for that name. Added
# last, so it runs first.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)


@app.exception_handler(KeelError)
async def keel_error_handler(request: Request, exc: KeelError) -> JSONResponse:
    """One translation from a service failure to a status code.

    Routes used to do this each for themselves by reading the message - literally
    `if "already has" in result["error"]` - so rewording an error changed an HTTP status
    and every new route re-derived the same mapping."""
    return JSONResponse(status_code=exc.status, content=exc.as_dict())


app.include_router(library_router, prefix="/api")


@app.get("/health")
async def health_check():
    """`service`, `pid` and `catalog` are for `keel up` and `keel down`: whatever
    answers on the port has to be recognisable as Keel, serving this catalog, before it
    is reused, and it is stopped by the pid it reports rather than by one remembered in
    a file that may have outlived it."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "service": "keel",
        "pid": os.getpid(),
        "catalog": str(get_store().dir.resolve()),
    }


# Minimal browse-and-edit UI: one static file, no assets, no build step.
_INDEX = Path(__file__).parent / "static" / "index.html"


@app.get("/{full_path:path}", include_in_schema=False)
async def app_shell(full_path: str):
    """Serve the UI for every path the API did not claim.

    Views used to live behind a `#` because the API owned `/threats` and `/mitigations`
    at the root, so there was nowhere else for them to go. The API now sits under
    `/api`, which frees those paths: a view has a real URL that can be linked, opened
    cold, and read. Declared last, so `/api/*`, `/health` and `/docs` all match first.

    The `/api` namespace is excluded explicitly. Without that this route answers every
    unmatched API path with 200 and a page of HTML — a typo'd endpoint looks like it
    worked, and a rejected path (a traversal attempt, say) stops looking rejected.
    """
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(_INDEX)
