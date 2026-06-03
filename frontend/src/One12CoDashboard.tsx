import { useState, useEffect } from 'react';
import BreakoutBadge from './BreakoutBadge';

const API_BASE = import.meta.env.VITE_API_BASE || '';

interface One12CoStock {
  symbol: string;
  stock_name: string;
  close: number;
  volume: number;
  avg_volume_20d: number;
  volume_multiplier: number;
  rsi: number;
  atr_pct: number;
  proximity_to_6m_high: number | null;
  breakout_state: string;
  mri_score: number;
  condition_breakout_10d: boolean;
  ema_50: number;
  ema_200: number;
  rs_90d: number;
  last_date: string;
}

export default function One12CoDashboard({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [stocks, setStocks] = useState<One12CoStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/112co/breakouts`)
      .then(res => res.json())
      .then(data => setStocks(data || []))
      .catch(err => {
        console.error('112Co fetch error:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Scanning 112Co universe…</div>;
  if (error) return <div className="error-state">⚠️ Failed to load: {error}</div>;

  const brokenOut = stocks.filter(d => d.breakout_state === 'BROKEN_OUT');
  const ready = stocks.filter(d => d.breakout_state === 'READY_TO_BREAKOUT');
  const consolidating = stocks.filter(d => d.breakout_state === 'CONSOLIDATING');


  const renderTable = (items: One12CoStock[]) => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Stock</th>
            <th>₹</th>
            <th>Vol×</th>
            <th>RSI</th>
            <th>ATR%</th>
            <th>6m Prox</th>
            <th>MRI</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.symbol} className="clickable-row" onClick={() => onSelectStock(item)}>
              <td className="font-bold">
                <div>{item.symbol}</div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>{item.stock_name}</div>
              </td>
              <td>₹{parseFloat(String(item.close)).toLocaleString()}</td>
              <td style={{ color: item.volume_multiplier >= 1.3 ? '#22c55e' : '#94a3b8' }}>
                {item.volume_multiplier}x
              </td>
              <td style={{
                color: item.rsi > 75 ? '#ef4444' : item.rsi >= 55 ? '#22c55e' : '#f59e0b'
              }}>
                {item.rsi?.toFixed(1)}
              </td>
              <td>{item.atr_pct?.toFixed(1)}%</td>
              <td style={{
                color: item.proximity_to_6m_high !== null && item.proximity_to_6m_high >= -3
                  ? '#22c55e' : '#94a3b8'
              }}>
                {item.proximity_to_6m_high !== null ? `${item.proximity_to_6m_high}%` : '—'}
              </td>
              <td style={{
                color: item.mri_score >= 80 ? '#22c55e' : item.mri_score >= 60 ? '#f59e0b' : '#ef4444'
              }}>
                {item.mri_score}
              </td>
              <td><BreakoutBadge state={item.breakout_state} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="watchlist">
      <h2 className="section-title">🔬 112Co Breakout Radar</h2>
      <p style={{ color: '#94a3b8', marginBottom: '8px' }}>
        Custom 112-company universe — PE expansion watchlist with MRI breakout detection.
      </p>
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', fontSize: '13px', color: '#64748b' }}>
        <span>🟢 BROKEN: {brokenOut.length}</span>
        <span>🟡 READY: {ready.length}</span>
        <span>⚪ CONSOLIDATING: {consolidating.length}</span>
        <span>📊 Total: {stocks.length}</span>
      </div>

      {stocks.length === 0 ? (
        <div className="empty-state">
          No 112Co data yet. Run the daily pipeline to populate indicators.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>

          {brokenOut.length > 0 && (
            <div>
              <h3 style={{ color: '#22c55e', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                🚀 Active Breakouts ({brokenOut.length})
              </h3>
              {renderTable(brokenOut)}
            </div>
          )}

          {ready.length > 0 && (
            <div>
              <h3 style={{ color: '#f59e0b', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                ⚡ Ready To Breakout ({ready.length})
              </h3>
              {renderTable(ready)}
            </div>
          )}

          {consolidating.length > 0 && (
            <div>
              <h3 style={{ color: '#94a3b8', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                📊 Consolidating ({consolidating.length})
              </h3>
              {renderTable(consolidating)}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
