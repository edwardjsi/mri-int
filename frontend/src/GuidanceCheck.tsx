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
          <h3 style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '10px' }}>📋 {symbol.toUpperCase()} — {result.total_promises || 0} promises</h3>
          {result.guidance.length === 0 ? <p style={{ color: '#64748b', fontSize: '0.8rem' }}>No guidance found.</p> : result.guidance.map((g: any, i: number) => (
            <div key={i} style={{ padding: '8px', marginBottom: '6px', background: '#1e293b', borderRadius: '5px', borderLeft: `3px solid ${g.status === 'ACHIEVED' ? '#22c55e' : g.status === 'MISSED' ? '#ef4444' : '#64748b'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.65rem', padding: '1px 6px', borderRadius: '3px', background: '#334155', color: '#94a3b8' }}>{g.guidance_type}</span>
                <span style={{ fontSize: '0.8rem' }}>{g.status === 'ACHIEVED' ? '✅' : g.status === 'MISSED' ? '❌' : g.status === 'PARTIAL' ? '⚠️' : g.status === 'PENDING' ? '⏳' : '⚡'}</span>
              </div>
              <p style={{ fontSize: '0.8rem', margin: '0 0 4px' }}>{g.guidance_text}</p>
              {g.target_value && <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Target: {g.target_value}{g.target_unit} | {g.confidence || '?'} confidence{g.actual_value ? ` | Actual: ${g.actual_value}` : ''}{g.variance_pct != null ? ` | ${g.variance_pct > 0 ? '+' : ''}${g.variance_pct?.toFixed(1)}%` : ''}</div>}
            </div>
          ))}
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