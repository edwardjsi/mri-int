from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import psycopg2.extras
from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/admin", tags=["admin"])

logger = logging.getLogger("mri_api.admin")

def verify_admin(client=Depends(get_current_client), conn=Depends(get_db)):
    """Dependency to check if the current user is an admin."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT is_admin FROM clients WHERE id = %s", (str(client["id"]),))
        record = cur.fetchone()
        cur.close()
        
        is_admin = False
        if record:
            # Tuple-safe check
            is_admin = record[0] if isinstance(record, (list, tuple)) else record.get("is_admin", False)

        if not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return client
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ADMIN VERIFY CRASH: {e}")
        raise HTTPException(status_code=500, detail=f"Admin verification failed: {e}")

@router.get("/metrics")
def get_metrics(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Get 30,000 foot view metrics of the MRI platform."""
    cur = conn.cursor()
    try:
        # Ensure tables exist
        cur.execute("CREATE TABLE IF NOT EXISTS client_watchlist (client_id UUID, symbol TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS client_external_holdings (client_id UUID, symbol TEXT, quantity NUMERIC, avg_cost NUMERIC)")

        cur.execute("SELECT COUNT(*) FROM clients")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT client_id) FROM client_watchlist")
        active_watchlists = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT client_id) FROM client_external_holdings")
        active_portfolios = cur.fetchone()[0]

        cur.execute("SELECT MAX(date) FROM daily_prices")
        last_ingestion = cur.fetchone()[0]

        return {
            "total_users": total_users,
            "active_watchlists": active_watchlists,
            "active_portfolios": active_portfolios,
            "last_ingestion": str(last_ingestion) if last_ingestion else None
        }
    except Exception as e:
        logger.error(f"METRICS ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Metrics Error: {str(e)}"})
    finally:
        cur.close()

@router.get("/top-stocks")
def get_top_stocks(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Get the leaderboard of top watched and top held stocks globally (anonymized)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Top 15 watched stocks
        cur.execute("""
            SELECT symbol, COUNT(*) as count 
            FROM client_watchlist 
            GROUP BY symbol 
            ORDER BY count DESC 
            LIMIT 15
        """)
        top_watched = cur.fetchall()

        # Top 15 held stocks
        cur.execute("""
            SELECT symbol, COUNT(*) as count, SUM(quantity) as total_shares 
            FROM client_external_holdings 
            GROUP BY symbol 
            ORDER BY count DESC 
            LIMIT 15
        """)
        top_held = cur.fetchall()

        return {
            "top_watched": [dict(r) for r in top_watched],
            "top_held": [dict(r) for r in top_held]
        }
    except Exception as e:
        logger.error(f"TOP STOCKS ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Top Stocks Error: {str(e)}"})
    finally:
        cur.close()


@router.get("/clients")
def get_clients(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch list of all clients for admin selection."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id, email, name, is_active FROM clients ORDER BY name")
        clients = cur.fetchall()
        return [dict(c) for c in clients]
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()


@router.get("/clients/{client_id}/portfolio")
def get_client_portfolio(client_id: str, conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch specific client's portfolio with MRI grades for admin review."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get latest score for each symbol in holdings
        cur.execute("""
            SELECT eh.symbol, eh.quantity, eh.avg_cost, ss.total_score, ss.date as last_score_date
            FROM client_external_holdings eh
            LEFT JOIN (
                SELECT symbol, total_score, date FROM stock_scores s1
                WHERE date = (SELECT MAX(date) FROM stock_scores WHERE symbol = s1.symbol)
            ) ss ON ss.symbol = eh.symbol
            WHERE eh.client_id = %s
        """, (client_id,))
        holdings = cur.fetchall()
        return [dict(h) for h in holdings]
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()
