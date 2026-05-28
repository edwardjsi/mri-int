// @ts-nocheck
import { useState } from 'react';
import { api } from './api';

export default function GuidanceCheck() {
  const [symbol, setSymbol] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const check = async () => {
    if (!symbol.trim()) return;
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await api.getGuidanceDashboard(symbol.toUpperCase());
      setResult(data);
    } catch (e: any) { setError(e.message || 'Failed'); }
    finally { setLoading(false); }
  };

  const worst = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await api.getGuidanceLeaderboard(true, 10);
      setResult({ leaderboard: data });
    } catch (e: any) { setError(e.message || 'Failed'); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ padding: '20px', color: '#e2e8f0' }}>
      <h2>🔍 GuidanceCheck</h2>
      <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: '16px' }}>
        Management Credibility Tracker
      </p>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
        <input value={symbol} onChange={e => setSymbol(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && check()}
          placeholder="Symbol (e.g. TCS)"
          style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', padding: '8px 12px', color: '#e2e8f0', width: '180px' }} />
        <button onClick={check} disabled={loading}
          style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer', fontWeight: 600 }}>
          {loading ? '...' : 'Check'}
        </button>
        <button onClick={worst} disabled={loading}
          style={{ background: '#1e3a5f', color: '#60a5fa', border: '1px solid #3b82f6', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer' }}>
          Worst Offenders
        </button>
      </div>
      {error && <div style={{ padding: '12px', background: '#7f1d1d20', border: '1px solid #ef444440', borderRadius: '6px', color: '#fca5a5', marginBottom: '12px' }}>{error}</div>}
      {result && <pre style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px', color: '#94a3b8', fontSize: '0.8rem', maxHeight: '500px', overflow: 'auto' }}>{JSON.stringify(result, null, 2)}</pre>}
      {!result && !error && !loading && <p style={{ color: '#64748b' }}>Enter a symbol or click Worst Offenders.</p>}
    </div>
  );
}
