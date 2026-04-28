"""
Quality Investor Agents — Rule-based fundamental analysts.
Each agent evaluates a specific aspect of business quality.
"""

def safe_float(v):
    if v is None: return 0.0
    try:
        from decimal import Decimal
        import math
        if isinstance(v, Decimal) and v.is_nan(): return 0.0
        fv = float(v)
        if math.isnan(fv): return 0.0
        return fv
    except:
        return 0.0

def safe_div(num, den):
    fnum = safe_float(num)
    fden = safe_float(den)
    if fden == 0: return 0.0
    return fnum / fden

def get_growth(curr, prev):
    fcurr = safe_float(curr)
    fprev = safe_float(prev)
    if fprev == 0: return 0.0
    return (fcurr - fprev) / fprev

def get_trend(values):
    from decimal import Decimal
    import math
    
    # Filter out None, NaN, and other invalid values
    valid_values = []
    for v in values:
        if v is None: continue
        if isinstance(v, Decimal) and v.is_nan(): continue
        try:
            fv = float(v)
            if math.isnan(fv): continue
            valid_values.append(fv)
        except:
            continue

    if len(valid_values) < 2: return "neutral"
    if valid_values[-1] > valid_values[0]: return "up"
    if valid_values[-1] < valid_values[0]: return "down"
    return "flat"

# 1. REVENUE QUALITY AGENT
def revenue_quality_agent(financials):
    if len(financials) < 2:
        return {"score": 0, "reason": "Insufficient history", "confidence": 0}
    
    revs = [f['revenue'] for f in financials]
    margins = [safe_div(f['ebitda'], f['revenue']) for f in financials]
    
    latest_growth = get_growth(revs[-1], revs[-2])
    margin_trend = get_trend(margins)
    
    # Logic: Sales UP and Margins UP/Flat is High Quality
    if latest_growth > 0.12 and margin_trend != "down":
        score = 10
        reason = f"Strong growth ({latest_growth:.1%}) with healthy margins."
    elif latest_growth > 0.08:
        score = 7
        reason = f"Moderate growth ({latest_growth:.1%})."
    else:
        score = 3
        reason = "Weak or stagnant revenue growth."
        
    return {"score": score, "reason": reason, "confidence": 0.8}

# 2. MARGIN QUALITY AGENT
def margin_quality_agent(financials):
    margins = [safe_div(f['ebitda'], f['revenue']) for f in financials]
    m_trend = get_trend(margins)
    
    if m_trend == "up":
        score = 10
        reason = "Expansion driven by pricing power or product mix."
    elif m_trend == "flat":
        score = 7
        reason = "Stable margins indicating competitive positioning."
    else:
        score = 2
        reason = "Declining margins — potential cost pressures or loss of moat."
        
    return {"score": score, "reason": reason, "confidence": 0.9}

# 3. OPERATING LEVERAGE AGENT
def operating_leverage_agent(financials):
    if len(financials) < 2: return {"score": 5, "reason": "N/A"}
    
    f_curr = financials[-1]
    f_prev = financials[-2]
    
    rev_growth = get_growth(f_curr['revenue'], f_prev['revenue'])
    ebitda_growth = get_growth(f_curr['ebitda'], f_prev['ebitda'])
    
    # Rule: IF EBITDA growth >= 1.5x Sales growth -> Positive
    if ebitda_growth > 0 and rev_growth > 0 and ebitda_growth >= (1.5 * rev_growth):
        score = 10
        reason = f"Significant operating leverage: EBITDA growing {ebitda_growth/rev_growth:.1f}x faster than sales."
    elif ebitda_growth > rev_growth:
        score = 7
        reason = "Positive operating leverage detected."
    else:
        score = 3
        reason = "Profits lagging revenue growth — inefficient scaling."
        
    return {"score": score, "reason": reason, "confidence": 0.7}

# 4. WORKING CAPITAL AGENT
def working_capital_agent(financials):
    if len(financials) < 2: return {"score": 5, "reason": "N/A"}
    
    f_curr = financials[-1]
    f_prev = financials[-2]
    
    rev_growth = get_growth(f_curr['revenue'], f_prev['revenue'])
    rec_growth = get_growth(f_curr['receivables'], f_prev['receivables'])
    
    # Red flag: Receivables growing faster than sales
    if rec_growth > rev_growth + 0.05:
        score = 2
        reason = f"Red Flag: Receivables (+{rec_growth:.1%}) outstripping sales (+{rev_growth:.1%})."
    else:
        score = 8
        reason = "Healthy working capital cycle."
        
    return {"score": score, "reason": reason, "confidence": 0.85}

# 5. CAPITAL EFFICIENCY AGENT (ROCE vs WACC)
def capital_efficiency_agent(financials, wacc=0.12):
    latest = financials[-1]
    roce = safe_div(latest['ebitda'], latest['capital_employed'])
    
    if roce > wacc + 0.05:
        score = 10
        reason = f"High value creation: ROCE ({roce:.1%}) significantly above WACC ({wacc:.1%})."
    elif roce > wacc:
        score = 7
        reason = f"Value creation: ROCE ({roce:.1%}) covers cost of capital."
    else:
        score = 0
        reason = f"Value Destruction: ROCE ({roce:.1%}) below WACC ({wacc:.1%})."
        
    return {"score": score, "reason": reason, "confidence": 1.0}

# 6. BUSINESS EVOLUTION AGENT
def business_evolution_agent(financials):
    # Detects TAM expansion/integration proxy via Asset Growth + Margin Stability
    asset_growth = get_trend([f['total_assets'] for f in financials])
    margin_stability = get_trend([safe_div(f['ebitda'], f['revenue']) for f in financials])
    
    if asset_growth == "up" and margin_stability != "down":
        score = 8
        reason = "Signs of structural expansion and capacity building."
    else:
        score = 5
        reason = "Steady state business evolution."
        
    return {"score": score, "reason": reason, "confidence": 0.5}

# 7. FINANCIAL TRANSLATION AGENT
def financial_translation_agent(financials):
    if len(financials) < 2: return {"score": 5, "reason": "N/A"}
    
    curr = financials[-1]
    prev = financials[-2]
    
    ebitda = safe_float(curr['ebitda'])
    rec_curr = safe_float(curr['receivables'])
    rec_prev = safe_float(prev['receivables'])
    net_profit = safe_float(curr['net_profit'])
    
    cash_gen_proxy = ebitda - (rec_curr - rec_prev)
    conversion_ratio = safe_div(cash_gen_proxy, net_profit)
    
    if conversion_ratio > 0.8:
        score = 10
        reason = f"High earnings quality: Cash conversion ratio {conversion_ratio:.1f}x."
    elif conversion_ratio > 0.5:
        score = 7
        reason = "Acceptable earnings quality."
    else:
        score = 2
        reason = f"Poor translation: Earnings not reflecting in cash (Ratio: {conversion_ratio:.1f}x)."
        
    return {"score": score, "reason": reason, "confidence": 0.8}
