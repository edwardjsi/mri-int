import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mri_api")

# Import routers
from api.auth import router as auth_router
from api.signals import router as signals_router
from api.actions import router as actions_router
from api.portfolio import router as portfolio_router
from api.portfolio_review import router as portfolio_review_router
from api.email_debug import router as email_debug_router
from api.watchlist import router as watchlist_router
from api.admin import router as admin_router
from api.fundamental import router as fundamental_router
from api.perx import router as perx_router
from api.v2.perx import router as perx_v2_router
from api.aae import router as aae_router
from api.breakout_status import router as breakout_router
from api.guidance import router as guidance_router
from api.unified import router as unified_router
from api.schema import ensure_required_tables
from engine_core.db import get_connection

load_dotenv()

app = FastAPI(title="MRI-Int API")

@app.on_event("startup")
def on_startup():
    logger.info("Syncing Database Schema...")
    conn = None
    try:
        conn = get_connection()
        ensure_required_tables(conn)
        logger.info("✅ Database Schema Synced")

        # Auto-prime guidance on first run (if guidance table is empty)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM public.management_guidance")
            guidance_count = cur.fetchone()[0]
            cur.close()
            if guidance_count == 0:
                logger.info("🔍 Guidance table is empty — auto-priming all stocks in background...")
                cur2 = conn.cursor()
                cur2.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM client_watchlist")
                wl = {row["symbol"] for row in cur2.fetchall()}
                cur2.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM client_external_holdings")
                hl = {row["symbol"] for row in cur2.fetchall()}
                cur2.close()
                all_syms = sorted(wl | hl)
                if all_syms:
                    import threading
                    def _prime():
                        from engine_guidance.guidance_primer import prime_guidance_data_batch
                        prime_guidance_data_batch(all_syms)
                    threading.Thread(target=_prime, daemon=True).start()
                    logger.info(f"🔍 Background priming started for {len(all_syms)} stocks")
        except Exception as e:
            logger.warning(f"Auto-prime check skipped: {e}")
    except Exception as e:
        logger.error(f"❌ Database Schema Sync FAILED: {e}")
    finally:
        if conn:
            conn.close()

# Custom Exception Handler to log validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error(f"Validation Error: {exc.errors()}")
    logger.error(f"Request Method: {request.method} URL: {request.url}")
    logger.error(f"Request Body: {body.decode() if body else 'EMPTY'}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body.decode() if body else None},
    )

# Always allow all origins to prevent any frontend deployment domain (Vercel/Netlify/Local) from being blocked
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_router)
app.include_router(signals_router)
app.include_router(actions_router)
app.include_router(portfolio_router)
app.include_router(portfolio_review_router)
app.include_router(email_debug_router)
app.include_router(watchlist_router)
app.include_router(admin_router)
app.include_router(fundamental_router)
app.include_router(perx_router)
app.include_router(perx_v2_router, prefix="/api/v2")
app.include_router(aae_router)
app.include_router(breakout_router)
app.include_router(guidance_router)
app.include_router(unified_router)

# Explicit Health Check (Must be before catch-all)
@app.api_route("/api/health", methods=["GET", "POST"])
async def health():
    import subprocess
    try:
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        branch, commit = "unknown", "unknown"
    return {"status": "healthy", "branch": branch, "commit": commit}

# Serve Frontend Static Files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    # Mount assets folder explicitly if it exists
    assets_path = os.path.join(static_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    @app.api_route("/{full_path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    async def serve_frontend(request: Request, full_path: str):
        # Allow API calls to pass through. If they reached here, they matched nothing in the routers.
        if full_path.startswith("api/") or full_path.startswith("auth/"):
             return JSONResponse(status_code=404, content={"detail": "Not Found"})

        # Only serve static files for GET/HEAD requests
        if request.method not in ("GET", "HEAD"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        # Check if the requested file exists in static/
        file_path = os.path.join(static_path, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Fallback to index.html for React Router
        index_path = os.path.join(static_path, "index.html")
        if os.path.exists(index_path):
            response = FileResponse(index_path)
            # Prevent caching of the entry point so users always get the latest JS bundle
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        
        return JSONResponse(status_code=404, content={"detail": "Static files not found"})
