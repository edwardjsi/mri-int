// @ts-nocheck
import { useState } from 'react';
import { api } from './api';

export default function GuidanceCheck() {
  const [symbol, setSymbol] = useState('');
  const [result, setResult] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [primeMsg, setPrimeMsg] = useState('');

  const check = async () => {
    if (!symbol.trim()) return;
    setLoading(true); setError(''); setResult(null);
    try { setResult(await api.getGuidanceDashboard(symbol.toUpperCase())); }
    catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const worst = async () => {
    setLoading(true); setError('');
    try { setLeaderboard(await api.getGuidanceLeaderboard(true, 20) || []); }
    catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const primeAll = async () => {
    setLoading(true); setError(''); setPrimeMsg('');
    try {
      const res = await fetch('/api/guidance/prime-all', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('mri_token') }
      });
      const data = await res.json();
      setPrimeMsg(`Priming ${data.total_symbols} stocks in background — ${data.symbols.slice(0,5).join(', ')}...`);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: '20px', color: '#e2e8f0' }}>
      <h2>🔍 GuidanceCheck</h2>
      <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: '16px' }}>Management Credibility Tracker</p>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        <input value={symbol} onChange={e => setSymbol(e.target.value)} onKeyDown={e => e.key === 'Enter' && check()}
          placeholder="Symbol (e.g. TCS)"
          style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', padding: '8px 12px', color: '#e2e8f0', width: '160px' }} />
        <button onClick={check} disabled={loading} style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer', fontWeight: 600 }}>
          {loading ? '...' : 'Check'}
        </button>
        <button onClick={worst} disabled={loading} style={{ background: '#1e3a5f', color: '#60a5fa', border: '1px solid #3b82f6', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer' }}>
          Worst Offenders
        </button>
        <button onClick={primeAll} disabled={loading} style={{ background: '#451a03', color: '#fbbf24', border: '1px solid #92400e', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer', fontWeight: 600 }}>
          ⚡ Prime All Stocks
        </button>
      </div>

      {primeMsg && <div style={{ padding: '10px', background: '#1e3a5f', border: '1px solid #3b82f6', borderRadius: '6px', color: '#93c5fd', marginBottom: '12px', fontSize: '0.85rem' }}>{primeMsg}</div>}

      {error && <div style={{ padding: '10px', background: '#7f1d1d20', border: '1px solid #ef444440', borderRadius: '6px', color: '#fca5a5', marginBottom: '12px' }}>{error}</div>}

      {result && result.guidance && (
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '10px' }}>
            📋 {symbol.toUpperCase()} — {result.total_promises || 0} promises
            {result.credibility && <span style={{ marginLeft: '12px', fontSize: '0.75rem', color: result.credibility.accuracy_pct >= 70 ? '#22c55e' : result.credibility.accuracy_pct >= 40 ? '#f59e0b' : '#ef4444' }}>
              {result.credibility.accuracy_pct?.toFixed(0)}% credible · {result.credibility.trend || '--'}
            </span>}
          </h3>
          {result.guidance.length === 0 ? (
            <p style={{ color: '#64748b', fontSize: '0.8rem' }}>No guidance found.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #1e293b', color: '#64748b', textAlign: 'left' }}>
                  <th style={{ padding: '6px 8px', width: '30px' }}>#</th>
                  <th style={{ padding: '6px 8px', width: '100px' }}>Promised Date</th>
                  <th style={{ padding: '6px 8px' }}>Promise</th>
                  <th style={{ padding: '6px 8px', width: '90px' }}>Target</th>
                  <th style={{ padding: '6px 8px', width: '110px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {result.guidance.map((g: any, i: number) => {
                  const st = g.status;
                  const label = st === 'ACHIEVED' ? 'Fulfilled' : st === 'MISSED' ? 'Broken' : st === 'PARTIAL' ? 'Lagging' : st === 'PENDING' ? 'Awaiting' : 'Pending';
                  const clr = st === 'ACHIEVED' ? '#22c55e' : st === 'MISSED' ? '#ef4444' : st === 'PARTIAL' ? '#f59e0b' : '#64748b';
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid #1e293b', verticalAlign: 'top' }}>
                      <td style={{ padding: '6px 8px', color: '#475569' }}>{i + 1}</td>
                      <td style={{ padding: '6px 8px', whiteSpace: 'nowrap' }}>{g.target_date || '—'}</td>
                      <td style={{ padding: '6px 8px' }}>
                        <div style={{ marginBottom: '2px' }}>{g.guidance_text}</div>
                        <span style={{ fontSize: '0.65rem', padding: '1px 5px', borderRadius: '3px', background: '#334155', color: '#94a3b8' }}>{g.guidance_type}</span>
                      </td>
                      <td style={{ padding: '6px 8px', whiteSpace: 'nowrap' }}>{g.target_value ? `${g.target_value}${g.target_unit || ''}` : '—'}</td>
                      <td style={{ padding: '6px 8px' }}>
                        <span style={{ fontWeight: 600, color: clr, fontSize: '0.75rem' }}>{label}</span>
                        {g.variance_pct != null && <div style={{ fontSize: '0.65rem', color: '#64748b' }}>{g.variance_pct > 0 ? '+' : ''}{g.variance_pct.toFixed(1)}%</div>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {leaderboard.length > 0 && (
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px' }}>
          <h3 style={{ fontSize: '0.85rem', color: '#ef4444', marginBottom: '10px' }}>🚨 Worst Offenders</h3>
          {leaderboard.map((r: any, i: number) => (
            <div key={i} onClick={() => { setSymbol(r.symbol); check(); }} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1e293b', fontSize: '0.82rem', cursor: 'pointer' }}>
              <span style={{ fontWeight: 600 }}>{r.symbol}</span>
              <span style={{ color: '#ef4444' }}>{r.accuracy_pct?.toFixed(0)}%</span>
              <span style={{ color: '#94a3b8' }}>{r.missed_count} missed</span>
              <span>{r.trend === 'IMPROVING' ? '🟢' : r.trend === 'DETERIORATING' ? '🔴' : '🟡'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}