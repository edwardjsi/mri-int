from __future__ import annotations
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def generate_perx_pdf(report: dict) -> BytesIO:
    """Generate a professional institutional PDF memo from a PERX report payload."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=24, textColor=colors.hexColor("#1d4ed8"), spaceAfter=20)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.darkgrey, spaceBefore=10, spaceAfter=10)
    label_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontSize=10, fontWeight='bold', textColor=colors.grey)
    value_style = ParagraphStyle('ValueStyle', parent=styles['Normal'], fontSize=12, fontWeight='bold')
    text_style = ParagraphStyle('TextStyle', parent=styles['Normal'], fontSize=11, leading=16)

    elements = []

    # 1. Header
    elements.append(Paragraph("PERX INSTITUTIONAL REPORT", title_style))
    elements.append(Paragraph(f"<b>{report.get('company_name', report.get('symbol', 'UNKNOWN'))}</b>", styles['Heading2']))
    elements.append(Paragraph(f"Symbol: {report.get('symbol', 'UNKNOWN')} | Sector: {report.get('header', {}).get('sector', 'UNKNOWN')}", styles['Normal']))
    elements.append(Paragraph(f"Generated: {report.get('header', {}).get('report_timestamp', 'N/A')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # 2. PERX Score & Phase
    score_data = [
        [Paragraph("PERX RERATING SCORE", label_style), Paragraph("LIFECYCLE PHASE", label_style)],
        [Paragraph(f"{report.get('header', {}).get('perx_score', 'N/A')}/100", value_style), Paragraph(report.get('header', {}).get('lifecycle_phase', 'UNKNOWN'), value_style)]
    ]
    t = Table(score_data, colWidths=[200, 200])
    t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # 3. Executive Summary
    elements.append(Paragraph("EXECUTIVE SUMMARY", header_style))
    elements.append(Paragraph(report.get('executive_summary', 'No summary available.'), text_style))
    elements.append(Spacer(1, 15))

    # 4. Narrative Transition
    elements.append(Paragraph("NARRATIVE TRANSITION", header_style))
    elements.append(Paragraph(f"<b>Previous Market Perception:</b> {report.get('narrative_transition', {}).get('previous_market_perception', 'N/A')}", text_style))
    elements.append(Paragraph(f"<b>Emerging Market Perception:</b> {report.get('narrative_transition', {}).get('emerging_market_perception', 'N/A')}", text_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(report.get('narrative_transition', {}).get('why_this_matters', ''), text_style))
    elements.append(Spacer(1, 15))

    # 5. Engine Snapshot Table
    elements.append(Paragraph("ENGINE SNAPSHOT", header_style))
    snapshot = report.get('engine_outputs', {})
    snap_data = [
        ["Layer", "Score / Signal"],
        ["MRI Technical", f"{snapshot.get('mri', {}).get('total_score', 'N/A')}/100 (RS: {snapshot.get('mri', {}).get('relative_strength', 'N/A')})"],
        ["QIF Fundamental", f"{snapshot.get('qif', {}).get('score', 'N/A')}/100 ({snapshot.get('qif', {}).get('category', 'N/A')})"],
        ["STEE Setup", f"{snapshot.get('stee', {}).get('setup_quality_score', 'N/A')} (Ready: {snapshot.get('stee', {}).get('breakout_ready', 'N/A')})"],
        ["Thesis Fragility", snapshot.get('fragility', {}).get('level', 'N/A')]
    ]
    st = Table(snap_data, colWidths=[150, 250])
    st.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.hexColor("#f1f5f9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.hexColor("#475569")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.hexColor("#e2e8f0"))
    ]))
    elements.append(st)
    elements.append(Spacer(1, 15))

    # 5b. Investor Context Section
    inv_ctx = report.get('investor_context')
    if inv_ctx:
        elements.append(Paragraph("INVESTOR CONTEXT", header_style))
        
        inv_grade = inv_ctx.get('investor_grade', {})
        grade = inv_grade.get('grade', 'N/A')
        grade_summary = inv_grade.get('summary', '')
        elements.append(Paragraph(f"<b>Investor Grade: {grade}</b>", value_style))
        elements.append(Paragraph(grade_summary, text_style))
        elements.append(Spacer(1, 10))

        valuation = inv_ctx.get('valuation', {})
        earnings = inv_ctx.get('earnings_momentum', {})
        ownership = inv_ctx.get('ownership', {})
        liquidity = inv_ctx.get('liquidity', {})

        inv_data = [
            ["Factor", "Metric", "Detail"],
            ["Valuation (P/E)", f"{valuation.get('pe_ratio', 'N/A')}x", f"Sector: {valuation.get('sector_median_pe', 'N/A')}x | Hist: {valuation.get('pe_percentile_vs_history', 'N/A')}%ile"],
            ["Earnings Momentum", earnings.get('acceleration', 'N/A'), f"Rev: {earnings.get('revenue_growth_4q_pct', 'N/A')}% | Profit: {earnings.get('profit_growth_4q_pct', 'N/A')}%"],
            ["Ownership", ownership.get('promoter_trend', 'N/A'), f"Gov Score: {ownership.get('governance_score', 'N/A')} | Pledged: {ownership.get('pledged_pct', 'N/A')}%"],
            ["Liquidity", f"₹{liquidity.get('avg_daily_turnover_cr', 'N/A')}Cr", f"50L Position: {liquidity.get('days_to_build_50lac_position', 'N/A')} days"],
        ]

        peg = inv_ctx.get('peg_ratio', {})
        if peg.get('peg_ratio'):
            inv_data.append(["PEG Ratio", f"{peg['peg_ratio']}x", f"EPS Growth: {peg.get('eps_growth_pct', 'N/A')}%"])
        ev = inv_ctx.get('ev_ebitda', {})
        if ev.get('ev_ebitda'):
            inv_data.append(["EV/EBITDA", f"{ev['ev_ebitda']}x", f"Net Debt/EBITDA: {ev.get('net_debt_ebitda', 'N/A')}x"])
        inst = inv_ctx.get('institutional_flow', {})
        if inst.get('fii_holding_pct') or inst.get('dii_holding_pct'):
            fii_str = f"FII {inst.get('fii_trend', 'N/A')} ({inst.get('fii_change_qoq', '')}%)" if inst.get('fii_change_qoq') else f"FII: {inst.get('fii_holding_pct', 'N/A')}%"
            dii_str = f"DII {inst.get('dii_trend', 'N/A')} ({inst.get('dii_change_qoq', '')}%)" if inst.get('dii_change_qoq') else f"DII: {inst.get('dii_holding_pct', 'N/A')}%"
            inv_data.append(["Institutional Flow", fii_str, dii_str])

        inv_table = Table(inv_data, colWidths=[100, 120, 230])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.hexColor("#f1f5f9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.hexColor("#475569")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.hexColor("#e2e8f0"))
        ]))
        elements.append(inv_table)
        elements.append(Spacer(1, 10))

        # Pre-Mortem Risks
        pre_mortem = inv_ctx.get('pre_mortem', {})
        risks = pre_mortem.get('risks', [])
        if risks:
            elements.append(Paragraph("<b>Risk Pre-Mortem</b>", label_style))
            for risk in risks:
                elements.append(Paragraph(f"• {risk}", text_style))
            elements.append(Spacer(1, 10))

        # Catalyst Questions
        catalyst = inv_ctx.get('catalyst_questions', [])
        if catalyst:
            elements.append(Paragraph("<b>Catalyst Checklist</b>", label_style))
            elements.append(Paragraph("What to investigate next to build (or break) the rerating thesis:", text_style))
            for q in catalyst[:4]:
                elements.append(Paragraph(f"→ {q}", text_style))
            homework = inv_ctx.get('homework_note', '')
            if homework:
                elements.append(Spacer(1, 6))
                elements.append(Paragraph(f"<i>{homework}</i>", text_style))
            elements.append(Spacer(1, 15))

        # Historical Analogs
        analogs = inv_ctx.get('historical_analogs', {})
        analog_list = analogs.get('analogs', [])
        if analog_list:
            elements.append(Paragraph("<b>Historical Rerating Analogs</b>", label_style))
            for a in analog_list[:3]:
                elements.append(Paragraph(f"  {a.get('symbol', '?')} | Score: {a.get('score', 'N/A')} | {a.get('scan_date', '')}", text_style))
            hw = analogs.get('homework', '')
            if hw:
                elements.append(Paragraph(hw, text_style))
            elements.append(Spacer(1, 15))

    # 6. Final Verdict
    elements.append(Paragraph("FINAL INSTITUTIONAL VERDICT", header_style))
    elements.append(Paragraph(report['final_institutional_verdict'], text_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
