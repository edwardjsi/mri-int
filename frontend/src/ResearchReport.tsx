import { useState, useEffect } from 'react';
import { api } from './api';

export default function ResearchReport({ symbol, onBack }: { symbol: string; onBack: () => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [aaeData, setAaeData] = useState<any>(null);
  const [aaeLoading, setAaeLoading] = useState(false);

  useEffect(() => {
    if (!symbol) { setLoading(false); return; }
    api.getResearchReport(symbol)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [symbol]);

  useEffect(() => {
    if (!symbol) return;
    setAaeLoading(true);
    const timer = setTimeout(() => setAaeLoading(false), 5000);
    api.getAaeScan(symbol)
      .then((r: any) => { if (r && !r.error) setAaeData(r); })
      .catch(() => {})
      .finally(() => { clearTimeout(timer); setAaeLoading(false); });
  }, [symbol]);

  if (!symbol) {
    return (
      <div className="watchlist">
        <h2 className="section-title">📊 Research Report</h2>
        <p style={{ color: '#94a3b8' }}>Click any stock to see the complete analysis here.</p>
        <button className="btn-secondary" onClick={onBack}>← Back</button>
      </div>
    );
  }

  if (loading) return <div className="loading">Loading research report...</div>;

  const tech = data?.technical;
  const mgmt = data?.management;
  const quality = data?.quality;
  const pe = data?.pe_expansion;
  const cas = data?.cas;

  const score = tech?.mri_score ?? 0;
  const gateItems = tech?.gates ? [
    { l: 'Trend Integrity (EMA 50 > 200)', v: tech.gates.ema_50_200, w: '25%' },
    { l: 'Long-term Bias (200 EMA Slope)', v: tech.gates.ema_200_slope, w: '25%' },
    { l: 'Outperformance (90d RS > 0)', v: tech.gates.rs, w: '20%' },
    { l: 'Near 6-Month High', v: tech.gates.six_m_high, w: '20%' },
    { l: 'Volume Surge (≥ 1.3× Avg)', v: tech.gates.volume, w: '10%' },
    { l: 'Breakout Confirmation', v: tech.gates.breakout_10d, w: '🚀 Bonus' },
    { l: 'Price Quality', v: tech.gates.price_quality, w: '✨ Bonus' },
  ] : [];

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1000px', margin: '0 auto' }}>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#60a5fa', cursor: 'pointer', fontSize: '13px', marginBottom: '16px' }}>
        ← Back to Dashboard
      </button>

      {/* Analyze trigger */}
      <div style={{ marginBottom: '16px', padding: '12px', borderRadius: '8px', background: '#1e293b', border: '1px solid #334155', fontSize: '12px', color: '#94a3b8' }}>
        This report shows available data. Missing sections can be generated on demand.
        <button className="btn-secondary" style={{ marginLeft: '12px', padding: '6px 16px', fontSize: '11px' }}
          onClick={async () => {
            const token = localStorage.getItem('mri_token');
            if (!token) { alert('Please log in first.'); return; }
            try {
              const r = await api.triggerFundamentalAnalysis(symbol);
              alert(r.message || 'Analysis queued! You will receive an email when ready.');
            } catch (e: any) {
              alert('Failed to trigger: ' + (e?.message || 'unknown error'));
            }
          }}>
          🔄 Fetch Full Analysis
        </button>
      </div>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '28px', color: '#e2e8f0' }}>{symbol}</h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '13px' }}>
            {data?.stock_name || ''} {tech?.close ? ` | ₹${parseFloat(String(tech.close)).toLocaleString()}` : ''}
            {tech?.breakout_state ? ` | ${tech.breakout_state}` : ''}
          </p>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '11px', color: '#64748b' }}>MRI Score</div>
          <div style={{ fontSize: '36px', fontWeight: 900, color: score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444' }}>
            {score}/100
          </div>
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Column 1: MRI 7 Gates */}
        <div>
          {gateItems.length > 0 && (
            <div className="card" style={{ padding: '16px', marginBottom: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>⚡ MRI Score Breakdown</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                {gateItems.map((g, i) => (
                  <div key={i} style={{ padding: '8px', border: '1px solid #334155', borderRadius: '6px', background: '#0f172a' }}>
                    <div style={{ fontSize: '10px', color: '#64748b', marginBottom: '2px' }}>{g.l}</div>
                    <div style={{ fontSize: '9px', color: '#475569' }}>Weight: {g.w}</div>
                    <div style={{ fontSize: '11px', marginTop: '4px', fontWeight: 700, color: g.v ? '#22c55e' : '#ef4444' }}>
                      {g.v ? '✅ PASS' : '❌ FAIL'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AAE */}
          {aaeLoading && <div className="card" style={{ padding: '16px', textAlign: 'center', fontSize: '12px', color: '#64748b' }}>Loading AAE institutional scan... (requires login)</div>}
          {!aaeLoading && !aaeData && <div className="card" style={{ padding: '16px', marginBottom: '16px', textAlign: 'center', fontSize: '11px', color: '#64748b', border: '1px dashed #334155' }}>
            🧠 AAE institutional scan requires login. Log in and click the stock again.
          </div>}
          {aaeData && (
            <div className="card" style={{ padding: '16px', marginBottom: '16px', border: '1px solid #4338ca', background: '#1e1b4b' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#818cf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                🧠 AAE Institutional Scan
                <span style={{ float: 'right', fontSize: '20px', fontWeight: 900, color: aaeData.master_score >= 80 ? '#22c55e' : '#60a5fa' }}>{aaeData.master_score}</span>
              </h3>
              {aaeData.bull_case && (
                <div style={{ padding: '8px', background: 'rgba(34,197,94,0.1)', borderRadius: '6px', fontSize: '11px', color: '#4ade80' }}>
                  <strong>🐂 Bull:</strong> {(aaeData.bull_case || '').split('\n').filter((l: string) => l.trim().startsWith('-') || l.trim().startsWith('•'))[0] || (aaeData.bull_case || '').split('\n')[0]}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Column 2 */}
        <div>
          {/* CAS 6 Gates */}
          {cas && cas.gates && cas.gates.length > 0 && (
            <div className="card" style={{ padding: '16px', marginBottom: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                🛒 Breakout Decision ({cas.passed}/{cas.total} passed)
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                {cas.gates.map((g: any, i: number) => (
                  <div key={i} style={{ padding: '6px 8px', border: '1px solid #334155', borderRadius: '4px', fontSize: '10px', background: '#0f172a' }}>
                    <div style={{ color: '#64748b', marginBottom: '2px' }}>{g.label}</div>
                    {g.detail && <div style={{ fontSize: '9px', color: '#475569' }}>{g.detail}</div>}
                    <div style={{ fontWeight: 700, color: g.pass ? '#22c55e' : '#ef4444' }}>{g.pass ? '✅' : '❌'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Management Credibility */}
          {mgmt ? (
            <div className="card" style={{ padding: '16px', marginBottom: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🗣️ Management Credibility</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                {[{l:'Verdict',v:mgmt.current_verdict||'N/A',c:'#60a5fa'},{l:'Accuracy',v:mgmt.accuracy_pct?`${mgmt.accuracy_pct.toFixed(0)}%`:'N/A',c:mgmt.accuracy_pct>=70?'#22c55e':'#f59e0b'},{l:'Promises',v:`${mgmt.total_promises||0} total`},{l:'Trend',v:mgmt.trend||'N/A',c:mgmt.trend==='IMPROVING'?'#22c55e':mgmt.trend==='DETERIORATING'?'#ef4444':'#94a3b8'}].map((s,i)=>(
                  <div key={i} style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                    <div style={{ fontSize: '10px', color: '#64748b' }}>{s.l}</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: s.c || '#e2e8f0' }}>{s.v}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding: '16px', marginBottom: '16px', textAlign: 'center', border: '1px dashed #334155' }}>
              <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px' }}>🗣️ Management credibility data not yet processed</div>
              <div style={{ fontSize: '10px', color: '#475569' }}>Click "Fetch Full Analysis" above to analyze concall transcripts.</div>
            </div>
          )}

          {/* PE Expansion */}
          {pe ? (
            <div className="card" style={{ padding: '16px', marginBottom: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📊 PE Expansion Signal</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Score</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: pe.score >= 70 ? '#22c55e' : '#f59e0b' }}>{pe.score}</div>
                </div>
                <div style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Generated</div>
                  <div style={{ fontSize: '14px', fontWeight: 700 }}>{pe.generated_at ? new Date(pe.generated_at).toLocaleDateString() : 'N/A'}</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding: '16px', marginBottom: '16px', textAlign: 'center', border: '1px dashed #334155' }}>
              <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px' }}>📊 PE Expansion data not yet processed</div>
              <div style={{ fontSize: '10px', color: '#475569' }}>Click "Fetch Full Analysis" above to run institutional re-rating scan.</div>
            </div>
          )}

          {/* Quality Fundamentals */}
          {quality && quality.category ? (
            <div className="card" style={{ padding: '16px', marginBottom: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📊 Quality Fundamentals</h3>
              <div style={{ fontSize: '13px', fontWeight: 700, marginBottom: '8px' }}>{quality.category}</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                {[{l:'Revenue',v:quality.revenue_score},{l:'Margins',v:quality.margin_score},{l:'Leverage',v:quality.leverage_score},{l:'Working Cap',v:quality.wc_score},{l:'ROCE',v:quality.roce_score},{l:'Evolution',v:quality.evolution_score}].map((s,i)=>(
                  <div key={i} style={{ padding: '6px', textAlign: 'center', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                    <div style={{ fontSize: '9px', color: '#64748b' }}>{s.l}</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: (s.v ?? 0) >= 7 ? '#22c55e' : (s.v ?? 0) >= 5 ? '#f59e0b' : '#ef4444' }}>{s.v}/10</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding: '16px', marginBottom: '16px', textAlign: 'center', border: '1px dashed #334155' }}>
              <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px' }}>📊 Quality fundamentals not yet analyzed</div>
              <div style={{ fontSize: '10px', color: '#475569' }}>Click "Fetch Full Analysis" above to run QIF quality pipeline.</div>
            </div>
          )}
        </div>
      </div>

      {/* Primer / Guide */}
      <div className="card" style={{ padding: '20px', marginTop: '24px', border: '1px solid #334155', background: '#0f172a' }}>
        <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📖 Understanding This Report</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px', color: '#cbd5e1' }}>
          <div>
            <strong style={{ color: '#60a5fa' }}>⚡ MRI Score Breakdown</strong>
            <p style={{ margin: '4px 0', fontSize: '11px', color: '#64748b' }}>
              7 technical gates measuring momentum. Gates 1-5 are weighted (total 100%), gates 6-7 are bonus. 
              Score ≥ 80 = strong momentum. All 7 pass = 🚀 Golden Setup.
            </p>
          </div>
          <div>
            <strong style={{ color: '#60a5fa' }}>🛒 Breakout Decision</strong>
            <p style={{ margin: '4px 0', fontSize: '11px', color: '#64748b' }}>
              6 gates answering "should I buy this breakout?" 4+ passed = actionable. 
              Checks decision score, technicals, weekly resistance, volume, breakout age, and conviction.
            </p>
          </div>
          <div>
            <strong style={{ color: '#60a5fa' }}>🗣️ Management Credibility</strong>
            <p style={{ margin: '4px 0', fontSize: '11px', color: '#64748b' }}>
              Tracks what management promised in concall transcripts vs what they delivered. 
              Verdict zones: ADD ZONE (trustworthy), HOLD ZONE, THESIS BROKEN (consistently miss).
            </p>
          </div>
          <div>
            <strong style={{ color: '#60a5fa' }}>📊 PE Expansion Signal</strong>
            <p style={{ margin: '4px 0', fontSize: '11px', color: '#64748b' }}>
              Institutional re-rating score. High score + Growth/Expansion lifecycle = company 
              moving from value to growth phase. Derived from narrative analysis of transcripts.
            </p>
          </div>
          <div>
            <strong style={{ color: '#60a5fa' }}>📊 Quality Fundamentals</strong>
            <p style={{ margin: '4px 0', fontSize: '11px', color: '#64748b' }}>
              7-agent fundamental analysis from financial statements. Categories: Explosive Improver, 
              Stable Compounder, Turnaround, Value Trap, Distressed.
            </p>
          </div>
          <div>
            <strong style={{ color: '#60a5fa' }}>🧠 AAE Institutional Scan</strong>
            <p style={{ margin: '4px 0', fontSize: '11px', color: '#64748b' }}>
              10-layer forensic audit covering governance, structural signals, macro alignment, 
              and management integrity. Master score ≥ 80 = institutional-grade opportunity.
              <em style={{ display: 'block', marginTop: '4px', color: '#f59e0b' }}>
                Requires login. If blank, log in and click again.
              </em>
            </p>
          </div>
        </div>
      </div>

      {/* Email button */}
      {data && (
        <div style={{ marginTop: '24px', textAlign: 'center' }}>
          <button className="btn-secondary" onClick={async () => {
            const token = localStorage.getItem('mri_token');
            if (!token) { alert('Please log in first to receive the email report.'); return; }
            try {
              const r = await api.email112coReport(symbol);
              alert(r.message || 'Report queued! Check your inbox.');
            } catch (e: any) {
              const msg = e?.message || '';
              if (msg.includes('401') || msg.includes('unauthorized')) {
                alert('Session expired. Please log in again.');
              } else {
                alert('Failed to send email: ' + msg);
              }
            }
          }} style={{ padding: '10px 24px', fontSize: '14px' }}>
            📧 Email Full Report
          </button>
        </div>
      )}
    </div>
  );
}
