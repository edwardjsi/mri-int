"""
MRI Client Signal Platform — FastAPI Application
"""
import os
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.signals import router as signals_router
from api.actions import router as actions_router
from api.portfolio import router as portfolio_router
from api.portfolio_review import router as portfolio_review_router

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

# CORS — allow React frontend (configurable via env)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router)
app.include_router(signals_router)
app.include_router(actions_router)
app.include_router(portfolio_router)
app.include_router(portfolio_review_router)


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


@app.get("/api/db-debug")
def db_debug():
    """List all tables the app actually sees in the connected database."""
    from api.deps import get_db
    try:
        # Get one connection from the generator
        conn = next(get_db())
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [r["table_name"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
        
        cur.execute("SELECT current_database();")
        db_name = cur.fetchone()
        db_name = db_name["current_database"] if isinstance(db_name, dict) else db_name[0]
        
        cur.close()
        conn.close()
        return {
            "status": "connected",
            "database": db_name,
            "tables_found": tables,
            "url_host": os.getenv("DATABASE_URL", "").split("@")[-1].split("/")[0] if "@" in os.getenv("DATABASE_URL", "") else "hidden"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/admin/survivorship-check")
def survivorship_check(secret: str = ""):
    """
    TEST-01: Survivorship Bias Check — runs on Render against real Neon DB.
    Usage: GET /api/admin/survivorship-check?secret=mri-admin-2024
    TEMPORARY — remove after test is complete.
    """
    if secret != "mri-admin-2024":
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    from src.db import get_connection
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT EXTRACT(YEAR FROM date)::int AS year,
                   COUNT(DISTINCT symbol)       AS distinct_symbols,
                   COUNT(*)                     AS total_rows,
                   MIN(date)::text              AS first_date,
                   MAX(date)::text              AS last_date
            FROM daily_prices
            GROUP BY year
            ORDER BY year
        """)
        rows = cur.fetchall()

        cur.execute("SELECT MIN(date)::text FROM daily_prices")
        earliest = cur.fetchone()[0]

        cur.execute("""
            SELECT symbol, COUNT(*) AS days
            FROM daily_prices
            GROUP BY symbol
            ORDER BY days DESC
            LIMIT 10
        """)
        top_symbols = [{"symbol": r[0], "days": r[1]} for r in cur.fetchall()]

        cur.close()
        conn.close()

        yearly = [
            {"year": r[0], "distinct_symbols": r[1], "total_rows": r[2],
             "first_date": r[3], "last_date": r[4]}
            for r in rows
        ]

        counts = [r[1] for r in rows]
        variation_pct = round((max(counts) - min(counts)) / min(counts) * 100, 1) if counts else 0

        if variation_pct > 20:
            verdict = "PASS"
            diagnosis = "Universe varies significantly — historical constituents likely included."
        elif variation_pct > 5:
            verdict = "PARTIAL"
            diagnosis = "Some variation found but verify delisted stocks are present."
        else:
            verdict = "FAIL"
            diagnosis = "Symbol count is nearly flat — survivorship bias likely exists."

        return {
            "test": "TEST-01 Survivorship Bias Check",
            "verdict": verdict,
            "diagnosis": diagnosis,
            "variation_pct": variation_pct,
            "earliest_data": earliest,
            "min_symbols_any_year": min(counts),
            "max_symbols_any_year": max(counts),
            "yearly_breakdown": yearly,
            "top_10_symbols_by_history": top_symbols,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
