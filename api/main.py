"""
MRI Client Signal Platform — FastAPI Application
"""
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.signals import router as signals_router
from api.actions import router as actions_router
from api.portfolio import router as portfolio_router

app = FastAPI(
    title="MRI Signal Platform",
    description="Market Regime Intelligence — Client Signal API",
    version="1.0.0",
)

# Global exception handler — surface actual errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"ERROR: {exc}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": tb},
    )

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router)
app.include_router(signals_router)
app.include_router(actions_router)
app.include_router(portfolio_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "mri-signal-platform"}


@app.get("/api/db-test")
def db_test():
    """Test DB connectivity directly."""
    import os, psycopg2
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5433"),
            dbname=os.getenv("DB_NAME", "mri_db"),
            user=os.getenv("DB_USER", "mri_admin"),
            password=os.getenv("DB_PASSWORD", ""),
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM clients")
        count = cur.fetchone()[0]
        conn.close()
        return {"db": "connected", "clients_count": count, "password_set": bool(os.getenv("DB_PASSWORD"))}
    except Exception as e:
        return {"db": "failed", "error": str(e), "password_set": bool(os.getenv("DB_PASSWORD"))}

