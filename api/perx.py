from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import psycopg2.extras

from api.deps import get_current_client, get_db
from engine_perx.orchestrator import (
    fetch_perx_report,
    generate_perx_report,
    list_perx_reports_for_client,
    get_perx_score_history,
    list_perx_archive_for_client,
    generate_perx_comparison,
)
from engine_perx.pdf_generator import generate_perx_pdf
from engine_core.email_service import send_perx_report_email
from engine_core.db import get_connection

router = APIRouter(prefix="/api/perx", tags=["perx"])


def background_perx_email(client_id: str, recipient_email: str, client_name: str, report: dict, symbol: str):
    """Background task to send and log PERX report email."""
    success = send_perx_report_email(
        recipient_email=recipient_email,
        client_name=client_name,
        report=report,
    )
    
    # Log to DB using a fresh connection
    try:
        conn = get_connection()
        cur = conn.cursor()
        status_value = "SENT" if success else "FAILED"
        cur.execute(
            """
            INSERT INTO email_log (client_id, date, email_type, service, subject, status)
            VALUES (%s, CURRENT_DATE, 'PERX_REPORT', 'AWS_SES', %s, %s)
            """,
            (
                client_id,
                f"PERX Report: {symbol} (AUTO)",
                status_value,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        # We don't want background logging failures to crash anything, but we should know
        print(f"PERX Background Email Logging Error: {e}")


@router.post("/scan/{symbol}")
def scan_symbol(
    symbol: str,
    background_tasks: BackgroundTasks,
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
        
        # V3 AUTO-EMAIL: Ensure metadata exists then send
        client_email = client.get("email")
        if client_email:
            # Sync metadata one last time before emailing
            try:
                from engine_perx.sector import get_sector_context
                with conn.cursor() as cur:
                    get_sector_context(cur, symbol, result["report"]["header"].get("sector", "UNKNOWN"))
            except: pass
            
            background_tasks.add_task(
                background_perx_email,
                client_id=str(client["id"]),
                recipient_email=client_email,
                client_name=client.get("name") or "Investor",
                report=result["report"],
                symbol=symbol,
            )

        # Check for data warnings in the report
        data_warnings = result["report"].get("_data_warnings", [])

        return {
            "status": "ok",
            "report_id": result["report_id"],
            "report": result["report"],
            "data_warnings": data_warnings,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "DATA_MISSING",
                "detail": str(exc),
                "action": "Check that the symbol is valid and has market data available."
            }
        )
    except Exception as exc:
        # Try to extract structured error
        err = getattr(exc, "to_dict", None)
        if err:
            error_payload = err()
        else:
            error_payload = {
                "error": "PERX_SCAN_FAILED",
                "detail": str(exc),
                "action": "This is unexpected. Please try again or contact support."
            }
        raise HTTPException(status_code=500, detail=error_payload)


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


@router.get("/history/{symbol}")
def get_history(symbol: str, limit: int = 30, client=Depends(get_current_client), conn=Depends(get_db)):
    """PERX score trajectory over all scans for a symbol."""
    return get_perx_score_history(conn, symbol, limit=limit)


@router.get("/archive")
def get_archive(
    limit: int = 50,
    offset: int = 0,
    symbol: str | None = None,
    lifecycle_stage: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """List all PERX scans for the client with filters."""
    rows, total = list_perx_archive_for_client(
        conn, str(client["id"]),
        symbol=symbol, lifecycle_stage=lifecycle_stage,
        min_score=min_score, max_score=max_score,
        from_date=from_date, to_date=to_date,
        limit=limit, offset=offset,
    )
    return {"rows": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/compare")
def compare_symbols(
    symbol_a: str,
    symbol_b: str,
    include_debate: bool = False,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Side-by-side PERX comparison of two symbols."""
    try:
        result = generate_perx_comparison(
            conn=conn,
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            client_id=str(client["id"]),
            include_debate=include_debate,
        )
        return {"status": "ok", "comparison": result}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PERX compare failed: {exc}")


@router.get("/report/{report_id}/pdf")
def get_report_pdf(report_id: str, client=Depends(get_current_client), conn=Depends(get_db)):
    """Generate and stream the professional institutional PDF memo."""
    row = fetch_perx_report(report_id, conn, str(client["id"]))
    if not row:
        raise HTTPException(status_code=404, detail="PERX report not found")
    
    report_payload = row.get("report_json")
    if not isinstance(report_payload, dict):
        raise HTTPException(status_code=500, detail="Stored report is corrupted")
        
    pdf_buffer = generate_perx_pdf(report_payload)
    filename = f"PERX_{report_payload['symbol']}_{report_payload['header']['report_timestamp']}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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
