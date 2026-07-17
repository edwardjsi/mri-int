import { useState, useEffect } from 'react';
import { api } from './api';

const API_BASE = import.meta.env.VITE_API_BASE || '';

function fetchJson(url: string) {
  return fetch(url).then(r => r.json()).catch(() => null);
}

export default function ResearchReport({ symbol, onBack }: { symbol: string; onBack: () => void }) {
  const [tech, setTech] = useState<any>(null);
  const [cas, setCas] = useState<any>(null);
  const [quality, setQuality] = useState<any>(null);
  const [mgmt, setMgmt] = useState<any>(null);
  const [pe, setPe] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) { setLoading(false); return; }
    Promise.all([
      // Technical data from 112co breakouts (filter by symbol)
      fetchJson(`${API_BASE}/api/112co/breakouts`).then(data => {
        if (data) setTech(data.find((s: any) => s.symbol === symbol) || null);
      }),
      // CAS gates
      api.getCasData(symbol).then(setCas).catch(() => {}),
      // Quality verdict
      api.getQualityVerdict(symbol).then(setQuality).catch(() => {}),
      // Management credibility
      fetchJson(`${API_BASE}/api/guidance/credibility/${symbol}`).then(setMgmt).catch(() => {}),
      // PE Expansion
      fetchJson(`${API_BASE}/api/pe-expansion/${symbol}`).then(setPe).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [symbol]);

  if (!symbol) {
    return (
      <div className="watchlist">
        <h2 className="section-title">📊 Research Report</h2>
        <p style={{ color: '#94a3b8' }}>Click any stock and select "View Full Report" to see the complete analysis here.</p>
        <button className="btn-secondary" onClick={onBack}>← Back</button>
      </div>
    );
  }

  if (loading) return <div className="loading">Loading research report...</div>;

  const score = tech?.mri_score ?? 0;
  const gateItems = [
    { l: 'Trend Integrity (EMA 50 > 200)', v: tech?.gate_ema_50_200, w: '25%' },
    { l: 'Long-term Bias (200 EMA Slope)', v: tech?.gate_ema_200_slope, w: '25%' },
    { l: 'Outperformance (90d RS > 0)', v: tech?.gate_rs, w: '20%' },
    { l: 'Near 6-Month High', v: tech?.gate_6m_high, w: '20%' },
    { l: 'Volume Surge (≥ 1.3× Avg)', v: tech?.gate_volume, w: '10%' },
    { l: 'Breakout Confirmation', v: tech?.gate_breakout_10d, w: '🚀 Bonus' },
    { l: 'Price Quality', v: tech?.gate_price_quality, w: '✨ Bonus' },
  ];

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1000px', margin: '0 auto' }}>
      {/* Back button */}
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#60a5fa', cursor: 'pointer', fontSize: '13px', marginBottom: '16px' }}>
        ← Back to Dashboard
      </button>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '28px', color: '#e2e8f0' }}>{symbol}</h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '13px' }}>
            {tech?.stock_name || ''} {tech?.close ? `| ₹${parseFloat(String(tech.close)).toLocaleString()}` : ''}
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

        {/* Column 1: MRI 7 Gates + CAS 6 Gates */}
        <div>
          {/* MRI 7 Gates */}
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
        </div>

        {/* Column 2: CAS Gates + Management + PE */}
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
          {mgmt && (
            <div className="card" style={{ padding: '16px', marginBottom: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🗣️ Management Credibility</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Verdict</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: '#60a5fa' }}>{mgmt.current_verdict || 'N/A'}</div>
                </div>
                <div style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Accuracy</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: mgmt.accuracy_pct >= 70 ? '#22c55e' : '#f59e0b' }}>{mgmt.accuracy_pct ? `${mgmt.accuracy_pct.toFixed(0)}%` : 'N/A'}</div>
                </div>
                <div style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Promises</div>
                  <div style={{ fontSize: '14px', fontWeight: 700 }}>{mgmt.total_promises || 0} total</div>
                </div>
                <div style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Trend</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: mgmt.trend === 'IMPROVING' ? '#22c55e' : mgmt.trend === 'DETERIORATING' ? '#ef4444' : '#94a3b8' }}>{mgmt.trend || 'N/A'}</div>
                </div>
              </div>
            </div>
          )}

          {/* PE Expansion */}
          {pe && pe.score !== undefined && (
            <div className="card" style={{ padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📊 PE Expansion Signal</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Score</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: pe.score >= 70 ? '#22c55e' : '#f59e0b' }}>{pe.score}</div>
                </div>
                <div style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Lifecycle</div>
                  <div style={{ fontSize: '14px', fontWeight: 700 }}>{pe.lifecycle_stage || 'N/A'}</div>
                </div>
              </div>
            </div>
          )}

          {/* Quality Verdict */}
          {quality && quality.category && (
            <div className="card" style={{ padding: '16px', marginTop: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📊 Quality Fundamentals</h3>
              <div style={{ fontSize: '13px', fontWeight: 700, marginBottom: '8px' }}>{quality.category}</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                {[{l:'Revenue',v:quality.revenue_score},{l:'Margins',v:quality.margin_score},{l:'Leverage',v:quality.leverage_score},{l:'Working Cap',v:quality.wc_score},{l:'ROCE',v:quality.roce_score},{l:'Evolution',v:quality.evolution_score}].map((s,i) => (
                  <div key={i} style={{ padding: '6px', textAlign: 'center', border: '1px solid #334155', borderRadius: '4px', background: '#0f172a' }}>
                    <div style={{ fontSize: '9px', color: '#64748b' }}>{s.l}</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: (s.v ?? 0) >= 7 ? '#22c55e' : (s.v ?? 0) >= 5 ? '#f59e0b' : '#ef4444' }}>{s.v}/10</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AAE */}
          <AaeSection symbol={symbol} />
        </div>
      </div>

      {/* Email button */}
      <div style={{ marginTop: '24px', textAlign: 'center' }}>
        <button className="btn-secondary" onClick={() => {
          api.email112coReport(symbol)
            .then((r: any) => alert(r.message || 'Report queued!'))
            .catch(() => alert('Failed to send email.'));
        }} style={{ padding: '10px 24px', fontSize: '14px' }}>
          📧 Email Full Report
        </button>
      </div>
    </div>
  );
}

/** Mini section that fetches and shows AAE data. */
function AaeSection({ symbol }: { symbol: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getAaeScan(symbol)
      .then((r: any) => { if (r && !r.error) setData(r); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) return <div className="card" style={{ padding: '16px', marginTop: '16px', textAlign: 'center', fontSize: '12px', color: '#64748b' }}>Loading AAE data...</div>;
  if (!data) return null;

  return (
    <div className="card" style={{ padding: '16px', marginTop: '16px', border: '1px solid #4338ca', background: '#1e1b4b' }}>
      <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#818cf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        🧠 AAE Institutional Scan
        <span style={{ float: 'right', fontSize: '20px', fontWeight: 900, color: data.master_score >= 80 ? '#22c55e' : '#60a5fa' }}>{data.master_score}</span>
      </h3>
      {data.bull_case && (
        <div style={{ marginTop: '8px', padding: '8px', background: 'rgba(34,197,94,0.1)', borderRadius: '6px', fontSize: '11px', color: '#4ade80' }}>
          <strong>🐂 Bull:</strong> {(data.bull_case || '').split('\n').filter((l: string) => l.trim().startsWith('-') || l.trim().startsWith('•'))[0] || (data.bull_case || '').split('\n')[0]}
        </div>
      )}
    </div>
  );
}
