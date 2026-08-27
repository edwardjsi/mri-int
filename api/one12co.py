"""
112Co Universe API — dedicated endpoints for the 112-company breakout watchlist.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from api.deps import get_db, get_current_client
import psycopg2.extras
import logging
from datetime import datetime
import os

router = APIRouter(prefix="/api/112co", tags=["112Co Universe"])
log = logging.getLogger(__name__)


@router.get("/breakouts")
def get_112co_breakouts(conn=Depends(get_db)):
    """
    Return breakout radar for 112Co universe only.
    Sorted: BROKEN_OUT first, then READY_TO_BREAKOUT, then CONSOLIDATING, then MISSING.
    LEFT JOIN ensures stocks without Yahoo data still appear.
    Includes all 7 MRI gate conditions from stock_scores.
    """
    query = """
        SELECT
            COALESCE(dp.symbol, u.symbol) AS symbol,
            u.stock_name,
            dp.close,
            dp.volume,
            dp.avg_volume_20d,
            CASE WHEN dp.avg_volume_20d > 0
                 THEN ROUND((dp.volume::numeric / dp.avg_volume_20d), 2)
                 ELSE 0 END AS volume_multiplier,
            dp.rsi_14 AS rsi,
            dp.atr_14 AS atr,
            CASE WHEN dp.close > 0
                 THEN ROUND((dp.atr_14::numeric / dp.close * 100), 2)
                 ELSE 0 END AS atr_pct,
            CASE WHEN dp.rolling_high_6m > 0
                 THEN ROUND(((dp.close::numeric / dp.rolling_high_6m) - 1) * 100, 2)
                 ELSE NULL END AS proximity_to_6m_high,
            COALESCE(dp.breakout_state, 'MISSING') AS breakout_state,
            COALESCE(ss.total_score, 0) AS mri_score,
            COALESCE(ss.condition_ema_50_200, FALSE) AS gate_ema_50_200,
            COALESCE(ss.condition_ema_200_slope, FALSE) AS gate_ema_200_slope,
            COALESCE(ss.condition_rs, FALSE) AS gate_rs,
            COALESCE(ss.condition_6m_high, FALSE) AS gate_6m_high,
            COALESCE(ss.condition_volume, FALSE) AS gate_volume,
            COALESCE(ss.condition_breakout_10d, FALSE) AS gate_breakout_10d,
            COALESCE(ss.condition_price_quality, FALSE) AS gate_price_quality,
            dp.condition_breakout_10d,
            dp.ema_50,
            dp.ema_200,
            dp.rs_90d,
            dp.date AS last_date
        FROM universe_112co u
        LEFT JOIN (
            SELECT DISTINCT ON (symbol) *
            FROM daily_prices
            ORDER BY symbol, date DESC
        ) dp ON dp.symbol = u.symbol
        LEFT JOIN (
            SELECT DISTINCT ON (symbol) *
            FROM stock_scores
            ORDER BY symbol, date DESC
        ) ss ON ss.symbol = dp.symbol
        WHERE u.is_active = TRUE
        ORDER BY
            CASE COALESCE(dp.breakout_state, 'MISSING')
                WHEN 'BROKEN_OUT' THEN 1
                WHEN 'READY_TO_BREAKOUT' THEN 2
                WHEN 'CONSOLIDATING' THEN 3
                ELSE 4
            END,
            COALESCE(ss.total_score, 0) DESC,
            u.symbol
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return rows
    except Exception as e:
        log.error(f"112Co breakouts error: {e}")
        return []
    finally:
        cur.close()


@router.get("/summary")
def get_112co_summary(conn=Depends(get_db)):
    """
    Return summary counts: BROKEN_OUT, READY_TO_BREAKOUT, CONSOLIDATING, missing.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT
                COALESCE(dp.breakout_state, 'MISSING') AS state,
                COUNT(*) AS count
            FROM universe_112co u
            LEFT JOIN (
                SELECT DISTINCT ON (symbol) symbol, breakout_state
                FROM daily_prices
                ORDER BY symbol, date DESC
            ) dp ON dp.symbol = u.symbol
            WHERE u.is_active = TRUE
            GROUP BY COALESCE(dp.breakout_state, 'MISSING')
            ORDER BY state
        """)
        rows = cur.fetchall()
        summary = {r['state']: r['count'] for r in rows}
        cur.execute("SELECT COUNT(*) FROM universe_112co WHERE is_active = TRUE")
        summary['total'] = cur.fetchone()['count']
        return summary
    except Exception as e:
        log.error(f"112Co summary error: {e}")
        return {"error": str(e)}
    finally:
        cur.close()


@router.post("/add")
def add_112co_symbol(symbol: str, conn=Depends(get_db)):
    """Add a symbol to the 112Co universe."""
    sym = symbol.upper().strip()
    cur = conn.cursor()
    try:
        cur.execute("SELECT is_active FROM universe_112co WHERE symbol = %s", (sym,))
        row = cur.fetchone()
        if row:
            if row['is_active']:
                return {"status": "already_present", "symbol": sym}
            cur.execute("UPDATE universe_112co SET is_active = TRUE WHERE symbol = %s", (sym,))
            conn.commit()
            return {"status": "reactivated", "symbol": sym}
        cur.execute("INSERT INTO universe_112co (symbol, is_active) VALUES (%s, TRUE) ON CONFLICT DO NOTHING", (sym,))
        conn.commit()
        cur.execute("SELECT COUNT(*) AS c FROM daily_prices WHERE symbol = %s", (sym,))
        has_data = cur.fetchone()['c'] > 0
        if not has_data:
            try:
                from engine_core.ingestion_engine import load_stocks
                load_stocks([sym])
                cur.execute("SELECT COUNT(*) AS c FROM daily_prices WHERE symbol = %s", (sym,))
                has_data = cur.fetchone()['c'] > 0
            except Exception:
                pass
        status = "added_with_data" if has_data else "added_no_data"
        return {"status": status, "symbol": sym, "has_data": has_data}
    except Exception as e:
        log.error(f"112Co add error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        cur.close()


@router.post("/remove")
def remove_112co_symbol(symbol: str, conn=Depends(get_db)):
    sym = symbol.upper().strip()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE universe_112co SET is_active = FALSE WHERE symbol = %s", (sym,))
        conn.commit()
        return {"status": "removed", "symbol": sym}
    except Exception as e:
        log.error(f"112Co remove error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        cur.close()


@router.get("/search")
def search_112co_symbols(q: str = "", limit: int = 20, conn=Depends(get_db)):
    if not q or len(q.strip()) < 2:
        return []
    query = q.strip().upper()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        sql = """
            SELECT DISTINCT dp.symbol, NULL AS stock_name,
                   EXISTS (SELECT 1 FROM universe_112co u WHERE u.symbol = dp.symbol AND u.is_active = TRUE) AS in_universe
            FROM daily_prices dp
            WHERE dp.symbol ILIKE %s
            LIMIT %s
        """
        cur.execute(sql, (f'%{query}%', limit))
        results = cur.fetchall()
        if len(results) < limit:
            sql2 = """
                SELECT symbol, stock_name, TRUE AS in_universe
                FROM universe_112co
                WHERE stock_name ILIKE %s AND is_active = TRUE
                LIMIT %s
            """
            cur.execute(sql2, (f'%{query}%', limit - len(results)))
            existing = {r['symbol'] for r in results}
            for r in cur.fetchall():
                if r['symbol'] not in existing:
                    results.append(r)
        return results
    except Exception as e:
        log.error(f"112Co search error: {e}")
        return []
    finally:
        cur.close()


@router.post("/email/{symbol}")
def email_112co_report(
    symbol: str,
    background_tasks: BackgroundTasks,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    """Email a stock research summary to the authenticated user, including PE Expansion data."""
    sym = symbol.upper().strip()
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # 1. Technical data
        cur.execute("""
            SELECT dp.close, dp.volume, dp.ema_50, dp.ema_200,
                   dp.breakout_state, COALESCE(ss.total_score, 0) AS mri_score
            FROM daily_prices dp
            LEFT JOIN (
                SELECT DISTINCT ON (symbol) symbol, date, total_score
                FROM stock_scores
                ORDER BY symbol, date DESC
            ) ss ON ss.symbol = dp.symbol
            WHERE dp.symbol = %s
            ORDER BY dp.date DESC
            LIMIT 1
        """, (sym,))
        row = cur.fetchone()
        
        close = float(row['close']) if row and row['close'] else None
        score = row['mri_score'] if row else 0
        state = row['breakout_state'] if row else 'N/A'
        ema50 = float(row['ema_50']) if row and row['ema_50'] else None
        ema200 = float(row['ema_200']) if row and row['ema_200'] else None
        
        # 2. PE Expansion data
        pe_data = {}
        try:
            cur.execute("""
                SELECT pe_score AS score, generated_at
                FROM perx_pe_scores
                WHERE symbol = %s
                ORDER BY generated_at DESC
                LIMIT 1
            """, (sym,))
            pe_row = cur.fetchone()
            if pe_row:
                pe_data = dict(pe_row)
        except Exception:
            pass
        
        # 3. Quality / QIF data
        quality_label = ""
        try:
            cur.execute("""
                SELECT category, total_score
                FROM quality_verdicts
                WHERE symbol = %s
                ORDER BY date DESC
                LIMIT 1
            """, (sym,))
            q_row = cur.fetchone()
            if q_row:
                quality_label = f"{q_row['category']} ({q_row['total_score']}/100)"
        except Exception:
            pass
        
        # 4. Management Credibility
        mgmt_label = ""
        mgmt_detail = ""
        try:
            cur.execute("""
                SELECT total_promises, achieved_count, missed_count, accuracy_pct,
                       current_verdict, trend
                FROM management_credibility_scores
                WHERE symbol = %s
                LIMIT 1
            """, (sym,))
            m_row = cur.fetchone()
            if m_row:
                acc = m_row['accuracy_pct']
                acc_str = f"{acc:.0f}%" if acc else "N/A"
                mgmt_label = m_row['current_verdict'] or 'N/A'
                mgmt_detail = f"Promises: {m_row['total_promises']} total, Achieved: {m_row['achieved_count']}, Missed: {m_row['missed_count']}, Accuracy: {acc_str}, Trend: {m_row['trend']}"
        except Exception:
            pass
        
        pe_score = pe_data.get('score', 'N/A')
        pe_lifecycle = pe_data.get('lifecycle_stage', 'N/A')
        
        close_fmt = f"{close:,.2f}" if close else 'N/A'
        ema50_fmt = f"{ema50:,.2f}" if ema50 else 'N/A'
        ema200_fmt = f"{ema200:,.2f}" if ema200 else 'N/A'
        
        html = f"""<html>
<body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 30px; color: #1e293b; max-width: 600px; margin: 0 auto;">
    <div style="border-bottom: 3px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px;">
        <h1 style="margin: 0; font-size: 24px; color: #0f172a;">{sym}</h1>
        <p style="margin: 4px 0 0; color: #64748b; font-size: 13px;">MRI Intelligence Report</p>
    </div>

    <h3 style="font-size: 14px; color: #2563eb; margin: 20px 0 10px; text-transform: uppercase; letter-spacing: 0.05em;">\u26a1 Technical Summary</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Price</td><td style="padding: 8px; font-weight: 700;">\u20b9{close_fmt}</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">MRI Score</td><td style="padding: 8px; font-weight: 700; color: {'#22c55e' if (score or 0) >= 80 else '#f59e0b' if (score or 0) >= 60 else '#ef4444'};">{score}/100</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Breakout</td><td style="padding: 8px; font-weight: 700;">{state}</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Quality</td><td style="padding: 8px; font-weight: 700;">{quality_label or 'N/A'}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">EMA 50</td><td style="padding: 8px; font-weight: 700;">\u20b9{ema50_fmt}</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 8px; color: #64748b;">EMA 200</td><td style="padding: 8px; font-weight: 700;">\u20b9{ema200_fmt}</td></tr>
    </table>

    <h3 style="font-size: 14px; color: #2563eb; margin: 24px 0 10px; text-transform: uppercase; letter-spacing: 0.05em;">\ud83d\udcca PE Expansion Signal</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">PE Expansion Score</td><td style="padding: 8px; font-weight: 700;">{pe_score}</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 8px; color: #64748b;">Lifecycle Stage</td><td style="padding: 8px; font-weight: 700;">{pe_lifecycle}</td></tr>
    </table>

    <h3 style="font-size: 14px; color: #2563eb; margin: 24px 0 10px; text-transform: uppercase; letter-spacing: 0.05em;">\ud83d\udde3\ufe0f Management Credibility</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <tr><td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #64748b;">Verdict</td><td style="padding: 8px; font-weight: 700;">{mgmt_label}</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 8px; color: #64748b;">Details</td><td style="padding: 8px; font-weight: 700;">{mgmt_detail}</td></tr>
    </table>

    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0 12px;">
    <p style="font-size: 11px; color: #94a3b8; text-align: center;">
        MRI Intelligence Platform | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </p>
</body></html>"""
        
        def _send():
            from engine_core.email_service import send_email_custom
            try:
                result = send_email_custom(
                    client['email'],
                    f"MRI Research Report: {sym}",
                    html
                )
                if result:
                    log.info(f"Email sent for {sym} to {client['email']}")
                else:
                    log.warning(f"Email send returned False for {sym} to {client['email']}")
            except Exception as e:
                log.error(f"Email send failed for {sym}: {e}")
        
        background_tasks.add_task(_send)
        return {"status": "QUEUED", "message": f"Research report for {sym} queued for email to {client['email']}."}
    except Exception as e:
        log.error(f"112Co email error: {e}")
        return {"status": "ERROR", "message": str(e)}
    finally:
        cur.close()


@router.get("/research/{symbol}")
def get_research_report(symbol: str, conn=Depends(get_db)):
    """Return ALL research data for a symbol in one shot."""
    sym = symbol.upper().strip()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # 1. Technical + Gates from daily_prices + stock_scores
        cur.execute("""
            SELECT dp.close, dp.volume, dp.avg_volume_20d, dp.breakout_state, dp.breakout_age,
                   dp.weekly_close_above_resistance, dp.ema_50, dp.ema_200, dp.rs_90d,
                   dp.rsi_14, dp.atr_14, dp.rolling_high_6m,
                   COALESCE(ss.total_score, 0) AS mri_score,
                   COALESCE(ss.condition_ema_50_200, FALSE) AS gate_ema_50_200,
                   COALESCE(ss.condition_ema_200_slope, FALSE) AS gate_ema_200_slope,
                   COALESCE(ss.condition_rs, FALSE) AS gate_rs,
                   COALESCE(ss.condition_6m_high, FALSE) AS gate_6m_high,
                   COALESCE(ss.condition_volume, FALSE) AS gate_volume,
                   COALESCE(ss.condition_breakout_10d, FALSE) AS gate_breakout_10d,
                   COALESCE(ss.condition_price_quality, FALSE) AS gate_price_quality
            FROM daily_prices dp
            LEFT JOIN (
                SELECT DISTINCT ON (symbol) *
                FROM stock_scores
                ORDER BY symbol, date DESC
            ) ss ON ss.symbol = dp.symbol
            WHERE dp.symbol = %s
            ORDER BY dp.date DESC
            LIMIT 1
        """, (sym,))
        tech = cur.fetchone()
        
        # 2. Management Credibility
        mgmt = {}
        try:
            cur.execute("""
                SELECT total_promises, achieved_count, missed_count, accuracy_pct,
                       current_verdict, trend
                FROM management_credibility_scores WHERE symbol = %s LIMIT 1
            """, (sym,))
            r = cur.fetchone()
            if r: mgmt = dict(r)
        except: pass
        
        # 3. Quality Verdict
        quality = {}
        try:
            cur.execute("""
                SELECT category, score, revenue_score, margin_score,
                       leverage_score, wc_score, roce_score, evolution_score
                FROM quality_verdicts WHERE symbol = %s ORDER BY updated_at DESC LIMIT 1
            """, (sym,))
            r = cur.fetchone()
            if r: quality = dict(r)
        except: pass
        
        # 4. PE Expansion
        pe = {}
        try:
            cur.execute("""
                SELECT pe_score AS score, generated_at
                FROM perx_pe_scores WHERE symbol = %s ORDER BY generated_at DESC LIMIT 1
            """, (sym,))
            r = cur.fetchone()
            if r: pe = dict(r)
        except: pass
        
        # 5. Stock name from universe
        stock_name = ""
        try:
            cur.execute("SELECT stock_name FROM universe_112co WHERE symbol = %s", (sym,))
            r = cur.fetchone()
            if r: stock_name = r['stock_name'] or ""
        except: pass
        
        # Build response
        result = {"symbol": sym, "stock_name": stock_name}
        
        if tech:
            close = float(tech['close']) if tech['close'] else None
            vol_mul = (tech['volume'] / tech['avg_volume_20d']) if tech.get('avg_volume_20d', 0) > 0 else 0
            mri = tech['mri_score'] or 0
            age = tech.get('breakout_age')
            
            result['technical'] = {
                "close": close,
                "volume": tech['volume'],
                "avg_volume_20d": tech['avg_volume_20d'],
                "volume_multiplier": round(vol_mul, 2),
                "breakout_state": tech.get('breakout_state', 'MISSING'),
                "breakout_age": age,
                "weekly_close_above_resistance": bool(tech['weekly_close_above_resistance']),
                "ema_50": float(tech['ema_50']) if tech['ema_50'] else None,
                "ema_200": float(tech['ema_200']) if tech['ema_200'] else None,
                "rs_90d": float(tech['rs_90d']) if tech['rs_90d'] else None,
                "rsi_14": float(tech['rsi_14']) if tech['rsi_14'] else None,
                "atr_14": float(tech['atr_14']) if tech['atr_14'] else None,
                "mri_score": mri,
                "gates": {
                    "ema_50_200": bool(tech['gate_ema_50_200']),
                    "ema_200_slope": bool(tech['gate_ema_200_slope']),
                    "rs": bool(tech['gate_rs']),
                    "six_m_high": bool(tech['gate_6m_high']),
                    "volume": bool(tech['gate_volume']),
                    "breakout_10d": bool(tech['gate_breakout_10d']),
                    "price_quality": bool(tech['gate_price_quality']),
                }
            }
            
            # CAS 6 gates
            cas_gates = [
                {"label": "1. Decision Score \u2265 85",  "pass": mri >= 85,  "detail": f"{mri}/85"},
                {"label": "2. MRI Technical \u2265 80",    "pass": mri >= 80,  "detail": f"{mri}/80"},
                {"label": "3. Weekly Close > Resistance",  "pass": bool(tech['weekly_close_above_resistance'])},
                {"label": "4. Volume \u2265 1.3\u00d7 Avg", "pass": vol_mul >= 1.3, "detail": f"{vol_mul:.2f}\u00d7"},
                {"label": "5. Breakout Age \u2264 15d",     "pass": age is not None and age <= 15, "detail": f"{age}d" if age is not None else "--"},
                {"label": "6. Overall Conviction \u2265 80%", "pass": mri >= 80, "detail": f"{mri}%"},
            ]
            result['cas'] = {
                "gates": cas_gates,
                "passed": sum(1 for g in cas_gates if g['pass']),
                "total": 6,
            }
        
        if mgmt:
            result['management'] = mgmt
        if quality:
            result['quality'] = quality
        if pe:
            result['pe_expansion'] = pe
        
        return result
    except Exception as e:
        log.error(f"Research report error for {sym}: {e}")
        return {"symbol": sym, "error": str(e)}
    finally:
        cur.close()


@router.post("/analyze/{symbol}")
def trigger_fundamental_analysis(
    symbol: str,
    background_tasks: BackgroundTasks,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    """Trigger on-demand fundamental analysis for a symbol. Runs QIF, Guidance, and AAE. Emails results."""
    sym = symbol.upper().strip()
    
    def _run_analysis():
        import logging
        log = logging.getLogger("mri_api.analyze")
        results = []
        
        try:
            # 1. Prime guidance (concall transcripts + management promises)
            from engine_guidance.guidance_primer import prime_guidance_data
            prime_guidance_data(sym)
            results.append("Management guidance primed")
            log.info(f"Guidance primed for {sym}")
        except Exception as e:
            results.append(f"Guidance skipped: {e}")
            log.warning(f"Guidance prime failed for {sym}: {e}")
        
        try:
            # 2. AAE data (fundamental financials + governance)
            from engine_fundamental.aae_data_primer import prime_aae_data
            prime_aae_data(sym)
            results.append("AAE data primed")
            log.info(f"AAE primed for {sym}")
        except Exception as e:
            results.append(f"AAE skipped: {e}")
            log.warning(f"AAE prime failed for {sym}: {e}")
        
        try:
            # 3. Quality pipeline (QIF scores)
            from engine_fundamental.pipeline import run_quality_pipeline
            yf_sym = f"{sym}.NS" if not sym.endswith(".NS") and not sym.endswith(".BO") else sym
            run_quality_pipeline(yf_sym)
            results.append("Quality analysis complete")
            log.info(f"Quality pipeline done for {sym}")
        except Exception as e:
            results.append(f"Quality skipped: {e}")
            log.warning(f"Quality failed for {sym}: {e}")
        
        # Send email notification
        try:
            from engine_core.email_service import send_email_custom
            summary = "\n".join(f"- {r}" for r in results)
            html = f"""<html><body style="font-family: Arial; padding: 20px;">
                <h2>Analysis Complete: {sym}</h2>
                <p>The following analyses were completed:</p>
                <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px;">{summary}</pre>
                <p><a href="{os.getenv("FRONTEND_URL", "https://mri-api.up.railway.app")}/?page=research&symbol={sym}">View the full report</a></p>
            </body></html>"""
            ok = send_email_custom(client['email'], f"Analysis Complete: {sym}", html)
            if ok:
                log.info(f"Analysis email sent to {client['email']} for {sym}")
            else:
                log.warning(f"Analysis email failed for {sym}")
        except Exception as e:
            log.warning(f"Email notification failed: {e}")
    
    background_tasks.add_task(_run_analysis)
    return {
        "status": "QUEUED",
        "message": f"Analysis for {sym} has started. You will receive an email at {client['email']} when complete."
    }
