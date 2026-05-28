// @ts-nocheck
import { useState, useEffect } from 'react';
import { api } from './api';

interface GuidanceItem {
  id: number;
  guidance_type: string;
  guidance_text: string;
  target_value: number | null;
  target_unit: string;
  target_date: string;
  confidence: string;
  status: string | null;
  actual_value: number | null;
  variance_pct: number | null;
}

interface CredibilityScore {
  symbol: string;
  total_promises: number;
  achieved_count: number;
  missed_count: number;
  accuracy_pct: number;
  avg_variance_pct: number | null;
  trend: string;
}

export default function GuidanceCheck() {
  const [holdings, setHoldings] = useState<CredibilityScore[]>([]);
  const [leaderboard, setLeaderboard] = useState<CredibilityScore[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [guidance, setGuidance] = useState<GuidanceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState<string | null>(null);

  useEffect(() => {
    loadHoldings();
    loadLeaderboard();
  }, []);

  const loadHoldings = async () => {
    try {
      const res = await api.getPortfolioGuidance();
      setHoldings(res.holdings || []);
    } catch (e) {
      console.error('Failed to load holdings:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadLeaderboard = async () => {
    try {
      const res = await api.getGuidanceLeaderboard(true, 10);
      setLeaderboard(res || []);
    } catch (e) {
      console.error('Failed to load leaderboard:', e);
    }
  };

  const loadGuidance = async (symbol: string) => {
    setSelectedSymbol(symbol);
    try {
      const res = await api.getGuidanceDashboard(symbol);
      setGuidance(res.guidance || []);
    } catch (e) {
      console.error('Failed to load guidance:', e);
    }
  };

  const triggerScan = async (symbol: string) => {
    setScanning(symbol);
    try {
      await api.triggerGuidanceScan(symbol);
    } catch (e) {
      console.error('Scan failed:', e);
    }
    setTimeout(() => setScanning(null), 3000);
  };

  const trendIcon = (t: string) => {
    if (t === 'IMPROVING') return '🟢';
    if (t === 'DETERIORATING') return '🔴';
    return '🟡';
  };

  const statusIcon = (s: string) => {
    if (s === 'ACHIEVED') return '✅';
    if (s === 'MISSED') return '❌';
    if (s === 'PARTIAL') return '⚠️';
    if (s === 'PENDING') return '⏳';
    return '⚡';
  };

  return (
    <div style={{ padding: '20px', maxWidth: '900px', margin: '0 auto', color: '#e2e8f0' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>
          🔍 GuidanceCheck
        </h2>
        <p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '4px' }}>
          Management Credibility Tracker
        </p>
      </div>

      {/* Portfolio Section */}
      <div style={{
        background: '#0f172a', border: '1px solid #1e293b',
        borderRadius: '8px', padding: '16px', marginBottom: '20px'
      }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#94a3b8', marginBottom: '12px' }}>
          📊 Your Portfolio
        </h3>
        {holdings.length === 0 ? (
          <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
            {loading ? 'Loading...' : 'Add stocks to your portfolio to track management credibility.'}
          </p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ color: '#64748b', textAlign: 'left', borderBottom: '1px solid #1e293b' }}>
                <th style={{ padding: '8px' }}>Stock</th>
                <th style={{ padding: '8px' }}>Accuracy</th>
                <th style={{ padding: '8px' }}>Promises</th>
                <th style={{ padding: '8px' }}>Trend</th>
                <th style={{ padding: '8px' }}></th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => (
                <tr key={h.symbol} style={{ borderBottom: '1px solid #1e293b', cursor: 'pointer' }}
                    onClick={() => loadGuidance(h.symbol)}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#1e293b'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                  <td style={{ padding: '10px 8px', fontWeight: 600 }}>{h.symbol}</td>
                  <td style={{ padding: '10px 8px', color: h.accuracy_pct >= 70 ? '#22c55e' : h.accuracy_pct >= 40 ? '#eab308' : '#ef4444' }}>
                    {h.accuracy_pct?.toFixed(0)}%
                  </td>
                  <td style={{ padding: '10px 8px', color: '#94a3b8' }}>
                    {h.achieved_count}/{h.total_promises}
                  </td>
                  <td style={{ padding: '10px 8px' }}>
                    {trendIcon(h.trend)} {h.trend}
                  </td>
                  <td style={{ padding: '10px 8px' }}>
                    <button onClick={(e) => { e.stopPropagation(); triggerScan(h.symbol); }}
                            disabled={scanning === h.symbol}
                            style={{
                              background: '#1e3a5f', color: '#60a5fa', border: '1px solid #3b82f6',
                              borderRadius: '4px', padding: '4px 10px', cursor: 'pointer', fontSize: '0.75rem'
                            }}>
                      {scanning === h.symbol ? '...' : 'Scan'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Detail View */}
      {selectedSymbol && (
        <div style={{
          background: '#0f172a', border: '1px solid #334155',
          borderRadius: '8px', padding: '16px', marginBottom: '20px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#94a3b8', margin: 0 }}>
              📋 {selectedSymbol} — Guidance Timeline
            </h3>
            <button onClick={() => setSelectedSymbol(null)}
                    style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '1.2rem' }}>
              ×
            </button>
          </div>

          {guidance.length === 0 ? (
            <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
              No guidance statements found. Click Scan to extract from transcripts.
            </p>
          ) : (
            guidance.map((g, i) => (
              <div key={i} style={{
                padding: '10px', marginBottom: '8px',
                background: '#1e293b', borderRadius: '6px',
                borderLeft: `3px solid ${g.status === 'ACHIEVED' ? '#22c55e' : g.status === 'MISSED' ? '#ef4444' : '#64748b'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{
                    fontSize: '0.7rem', padding: '2px 6px', borderRadius: '3px',
                    background: '#334155', color: '#94a3b8', fontWeight: 600
                  }}>
                    {g.guidance_type}
                  </span>
                  <span style={{ fontSize: '1rem' }}>{statusIcon(g.status)}</span>
                </div>
                <p style={{ fontSize: '0.85rem', margin: '6px 0 4px', lineHeight: 1.4 }}>
                  {g.guidance_text}
                </p>
                {g.target_value && (
                  <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', gap: '16px' }}>
                    <span>Target: {g.target_value} {g.target_unit}</span>
                    {g.actual_value && <span>Actual: {g.actual_value}</span>}
                    {g.variance_pct && (
                      <span style={{ color: Math.abs(g.variance_pct) < 10 ? '#22c55e' : '#ef4444' }}>
                        {g.variance_pct > 0 ? '+' : ''}{g.variance_pct?.toFixed(1)}%
                      </span>
                    )}
                    <span style={{ color: '#60a5fa' }}>{g.confidence} confidence</span>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Worst Offenders Leaderboard */}
      <div style={{
        background: '#0f172a', border: '1px solid #1e293b',
        borderRadius: '8px', padding: '16px'
      }}>
        <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ef4444', marginBottom: '12px' }}>
          🚨 Worst Offenders (≥3 promises tracked)
        </h3>
        {leaderboard.length === 0 ? (
          <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
            Not enough data yet. Track more quarters.
          </p>
        ) : (
          leaderboard.map((r, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 0', borderBottom: '1px solid #1e293b', fontSize: '0.85rem',
              cursor: 'pointer'
            }} onClick={() => loadGuidance(r.symbol)}>
              <span style={{ fontWeight: 600 }}>{r.symbol}</span>
              <span style={{ color: '#ef4444' }}>{r.accuracy_pct?.toFixed(0)}%</span>
              <span style={{ color: '#94a3b8' }}>{r.missed_count} missed</span>
              <span>{trendIcon(r.trend)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
