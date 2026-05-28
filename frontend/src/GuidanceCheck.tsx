// @ts-nocheck
import { useState } from 'react';
import { api } from './api';

const trendIcon = (t: string) => t === 'IMPROVING' ? '🟢' : t === 'DETERIORATING' ? '🔴' : '🟡';
const statusIcon = (s: string) => ({ ACHIEVED: '✅', MISSED: '❌', PARTIAL: '⚠️', PENDING: '⏳' } as any)[s] || '⚡';

export default function GuidanceCheck() {
  const [holdings, setHoldings] = useState<any[]>([]);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [guidance, setGuidance] = useState<any[]>([]);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);

  const loadAll = async () => {
    setLoading(true); setError('');
    try {
      const [h, l] = await Promise.all([
        api.getPortfolioGuidance().catch(() => ({ holdings: [] })),
        api.getGuidanceLeaderboard(true, 20).catch(() => []),
      ]);
      setHoldings(h.holdings || []);
      setLeaderboard(l || []);
      setLoaded(true);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const loadGuidance = async (sym: string) => {
    setSelected(sym); setError('');
    try { const r = await api.getGuidanceDashboard(sym); setGuidance(r.guidance || []); }
    catch (e: any) { setError(e.message); }
  };

  return (
    <div style={{ padding: '20px', color: '#e2e8f0' }}>
      <h2>🔍 GuidanceCheck</h2>
      <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: '12px' }}>Management Credibility Tracker</p>

      {!loaded && (
        <button onClick={loadAll} disabled={loading}
          style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', padding: '10px 24px', cursor: 'pointer', fontWeight: 600 }}>
          {loading ? 'Loading...' : '📊 Load Dashboard'}
        </button>
      )}
      {error && <div style={{ padding: '10px', background: '#7f1d1d20', border: '1px solid #ef444440', borderRadius: '6px', color: '#fca5a5', margin: '12px 0' }}>{error}</div>}

      {loaded && (<>
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '10px' }}>📊 Tracked Companies</h3>
          {holdings.length === 0 ? <p style={{ fontSize: '0.8rem', color: '#64748b' }}>No data yet.</p> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead><tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #1e293b' }}>
                <th style={{ padding: '6px' }}>Stock</th><th style={{ padding: '6px' }}>Accuracy</th><th style={{ padding: '6px' }}>Promises</th><th style={{ padding: '6px' }}>Trend</th>
              </tr></thead>
              <tbody>{holdings.map(h => (
                <tr key={h.symbol} onClick={() => loadGuidance(h.symbol)} style={{ cursor: 'pointer', borderBottom: '1px solid #1e293b' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#1e293b')} onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td style={{ padding: '8px 6px', fontWeight: 600 }}>{h.symbol}</td>
                  <td style={{ padding: '8px 6px', color: h.accuracy_pct >= 70 ? '#22c55e' : h.accuracy_pct >= 40 ? '#eab308' : '#ef4444' }}>{h.accuracy_pct?.toFixed(0)}%</td>
                  <td style={{ padding: '8px 6px', color: '#94a3b8' }}>{h.achieved_count}/{h.total_promises}</td>
                  <td style={{ padding: '8px 6px' }}>{trendIcon(h.trend)} {h.trend}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>

        {selected && (
          <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', padding: '14px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <h3 style={{ fontSize: '0.85rem', color: '#94a3b8', margin: 0 }}>📋 {selected}</h3>
              <button onClick={() => { setSelected(''); setGuidance([]); }} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '1.1rem' }}>×</button>
            </div>
            {guidance.length === 0 ? <p style={{ fontSize: '0.8rem', color: '#64748b' }}>No guidance found.</p> : guidance.map((g, i) => (
              <div key={i} style={{ padding: '8px', marginBottom: '6px', background: '#1e293b', borderRadius: '5px', borderLeft: `3px solid ${g.status === 'ACHIEVED' ? '#22c55e' : g.status === 'MISSED' ? '#ef4444' : '#64748b'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.65rem', padding: '1px 5px', borderRadius: '3px', background: '#334155', color: '#94a3b8' }}>{g.guidance_type}</span>
                  <span>{statusIcon(g.status)}</span>
                </div>
                <p style={{ fontSize: '0.8rem', margin: '4px 0' }}>{g.guidance_text}</p>
                {g.target_value && <div style={{ fontSize: '0.7rem', color: '#64748b', display: 'flex', gap: '12px' }}>
                  <span>Target: {g.target_value}{g.target_unit}</span>
                  {g.actual_value && <span>Actual: {g.actual_value}</span>}
                  {g.variance_pct != null && <span style={{ color: Math.abs(g.variance_pct) < 10 ? '#22c55e' : '#ef4444' }}>{g.variance_pct > 0 ? '+' : ''}{g.variance_pct?.toFixed(1)}%</span>}
                </div>}
              </div>
            ))}
          </div>
        )}

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px' }}>
          <h3 style={{ fontSize: '0.85rem', color: '#ef4444', marginBottom: '10px' }}>🚨 Worst Offenders</h3>
          {leaderboard.length === 0 ? <p style={{ fontSize: '0.8rem', color: '#64748b' }}>Not enough data.</p> : leaderboard.map((r, i) => (
            <div key={i} onClick={() => loadGuidance(r.symbol)} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1e293b', fontSize: '0.82rem', cursor: 'pointer' }}>
              <span style={{ fontWeight: 600 }}>{r.symbol}</span>
              <span style={{ color: '#ef4444' }}>{r.accuracy_pct?.toFixed(0)}%</span>
              <span style={{ color: '#94a3b8' }}>{r.missed_count} missed</span>
              <span>{trendIcon(r.trend)}</span>
            </div>
          ))}
        </div>
      </>)}
    </div>
  );
}
