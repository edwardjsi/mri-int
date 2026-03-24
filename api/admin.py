import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/admin", tags=["admin"])

def verify_admin(client=Depends(get_current_client), conn=Depends(get_db)):
    """Dependency to check if the current user is an admin."""
    cur = conn.cursor()
    cur.execute("SELECT is_admin FROM clients WHERE id = %s", (str(client["id"]),))
    record = cur.fetchone()
    cur.close()
    
    if not record or not record[0]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return client

@router.get("/metrics")
def get_metrics(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Get 30,000 foot view metrics of the MRI platform."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM clients")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT client_id) FROM client_watchlist")
        active_watchlists = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT client_id) FROM client_external_holdings")
        active_portfolios = cur.fetchone()[0]

        return {
            "total_users": total_users,
            "active_watchlists": active_watchlists,
            "active_portfolios": active_portfolios
        }
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
            "top_watched": top_watched,
            "top_held": top_held
        }
    finally:
        cur.close()
