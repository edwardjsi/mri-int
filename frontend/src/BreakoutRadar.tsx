import { useState, useEffect } from 'react';
import { api } from './api';
import BreakoutBadge from './BreakoutBadge';

export default function BreakoutRadar({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [radarData, setRadarData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getBreakoutRadar()
      .then(data => setRadarData(data || []))
      .catch(err => console.error('Failed to fetch radar data', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Scanning universe…</div>;

  const brokenOut = radarData.filter(d => d.breakout_state === 'BROKEN_OUT');
  const ready = radarData.filter(d => d.breakout_state === 'READY_TO_BREAKOUT');
  const consolidating = radarData.filter(d => d.breakout_state === 'CONSOLIDATING');

  const renderTable = (items: any[]) => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Price</th>
            <th>Volume</th>
            <th>Trend</th>
            <th>Platform Interest</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.symbol} className="clickable-row" onClick={() => onSelectStock(item)}>
              <td className="font-bold">{item.symbol}</td>
              <td>₹{parseFloat(item.close).toLocaleString()}</td>
              <td>{parseInt(item.volume).toLocaleString()}</td>
              <td style={{ color: '#22c55e' }}>{item.ema_50 > item.ema_200 ? 'Bullish Stack' : 'Neutral'}</td>
              <td style={{ color: '#60a5fa' }}>{item.holders} Holders / {item.watchers} Watchers</td>
              <td><BreakoutBadge state={item.breakout_state} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="watchlist">
      <h2 className="section-title">🚀 Breakout Radar</h2>
      <p style={{ color: '#94a3b8', marginBottom: '24px' }}>
        All tracked stocks with breakout classification — broken-outs first, then setups, then consolidations.
      </p>

      {radarData.length === 0 ? (
        <div className="empty-state">No stocks in watchlist or portfolio.</div>
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
                ⚡ Coiled Springs — Ready To Breakout ({ready.length})
              </h3>
              {renderTable(ready)}
            </div>
          )}

          {consolidating.length > 0 && (
            <div>
              <h3 style={{ color: '#6b7280', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                ⏳ Consolidating ({consolidating.length})
              </h3>
              {renderTable(consolidating)}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
