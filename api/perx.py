from fastapi import APIRouter, Depends, HTTPException, Query
import psycopg2.extras

from api.deps import get_current_client, get_db
from engine_perx.orchestrator import fetch_perx_report, generate_perx_report, list_perx_reports_for_client
from engine_core.email_service import send_perx_report_email

router = APIRouter(prefix="/api/perx", tags=["perx"])


@router.post("/scan/{symbol}")
def scan_symbol(
    symbol: str,
    include_debate: bool = Query(False, description="Include the existing AI forensic review in the generated report."),
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    try:
        result = generate_perx_report(
            symbol=symbol,
            conn=conn,
            client_id=str(client["id"]),
            include_debate=include_debate,
            persist=True,
        )
        return {
            "status": "ok",
            "report_id": result["report_id"],
            "report": result["report"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PERX scan failed: {exc}")


@router.get("/report/{report_id}")
def get_report(report_id: str, client=Depends(get_current_client), conn=Depends(get_db)):
    row = fetch_perx_report(report_id, conn, str(client["id"]))
    if not row:
        raise HTTPException(status_code=404, detail="PERX report not found")
    return row


@router.get("/recent")
def get_recent_reports(limit: int = 10, client=Depends(get_current_client), conn=Depends(get_db)):
    return list_perx_reports_for_client(conn, str(client["id"]), limit=limit)


@router.get("/search")
def search_companies(q: str, conn=Depends(get_db)):
    """Autocomplete search for company name or symbol to power the PERX dropdown."""
    if not q or len(q) < 2:
        return []
    query = f"%{q.upper()}%"
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT symbol, company_name
            FROM universe
            WHERE symbol ILIKE %s OR company_name ILIKE %s
            LIMIT 10
        """, (query, query))
        return [dict(r) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        cur.close()


@router.post("/email/{report_id}")
def email_report(report_id: str, client=Depends(get_current_client), conn=Depends(get_db)):
    row = fetch_perx_report(report_id, conn, str(client["id"]))
    if not row:
        raise HTTPException(status_code=404, detail="PERX report not found")

    client_email = client.get("email")
    if not client_email:
        raise HTTPException(status_code=400, detail="Client email missing")

    report_payload = row.get("report_json")
    if not isinstance(report_payload, dict):
        raise HTTPException(status_code=500, detail="Stored PERX report payload is not readable")

    success = send_perx_report_email(
        recipient_email=client_email,
        client_name=client.get("name") or "Investor",
        report=report_payload,
    )

    status_value = "SENT" if success else "FAILED"
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO email_log (client_id, date, email_type, service, subject, status)
        VALUES (%s, CURRENT_DATE, %s, %s, %s, %s)
        """,
        (
            str(client["id"]),
            "PERX_REPORT",
            "AWS_SES",
            f"PERX Report: {row.get('symbol', 'UNKNOWN')}",
            status_value,
        ),
    )
    conn.commit()

    if not success:
        raise HTTPException(status_code=502, detail="PERX email send failed")

    return {
        "status": "sent",
        "report_id": report_id,
        "recipient": client_email,
    }
