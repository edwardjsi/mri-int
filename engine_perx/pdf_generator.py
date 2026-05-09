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
    elements.append(Paragraph(f"<b>{report['company_name']}</b>", styles['Heading2']))
    elements.append(Paragraph(f"Symbol: {report['symbol']} | Sector: {report['header'].get('sector', 'UNKNOWN')}", styles['Normal']))
    elements.append(Paragraph(f"Generated: {report['header'].get('report_timestamp', 'N/A')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # 2. PERX Score & Phase
    score_data = [
        [Paragraph("PERX RERATING SCORE", label_style), Paragraph("LIFECYCLE PHASE", label_style)],
        [Paragraph(f"{report['header']['perx_score']}/100", value_style), Paragraph(report['header']['lifecycle_phase'], value_style)]
    ]
    t = Table(score_data, colWidths=[200, 200])
    t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # 3. Executive Summary
    elements.append(Paragraph("EXECUTIVE SUMMARY", header_style))
    elements.append(Paragraph(report['executive_summary'], text_style))
    elements.append(Spacer(1, 15))

    # 4. Narrative Transition
    elements.append(Paragraph("NARRATIVE TRANSITION", header_style))
    elements.append(Paragraph(f"<b>Previous Market Perception:</b> {report['narrative_transition']['previous_market_perception']}", text_style))
    elements.append(Paragraph(f"<b>Emerging Market Perception:</b> {report['narrative_transition']['emerging_market_perception']}", text_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(report['narrative_transition']['why_this_matters'], text_style))
    elements.append(Spacer(1, 15))

    # 5. Engine Snapshot Table
    elements.append(Paragraph("ENGINE SNAPSHOT", header_style))
    snapshot = report['engine_outputs']
    snap_data = [
        ["Layer", "Score / Signal"],
        ["MRI Technical", f"{snapshot['mri']['total_score']}/100 (RS: {snapshot['mri']['relative_strength']})"],
        ["QIF Fundamental", f"{snapshot['qif']['score']}/100 ({snapshot['qif']['category']})"],
        ["STEE Setup", f"{snapshot['stee']['setup_quality_score']} (Ready: {snapshot['stee']['breakout_ready']})"],
        ["Thesis Fragility", snapshot['fragility']['level']]
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

    # 6. Final Verdict
    elements.append(Paragraph("FINAL INSTITUTIONAL VERDICT", header_style))
    elements.append(Paragraph(report['final_institutional_verdict'], text_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
