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

  const freshBreakouts = radarData.filter(d => d.breakout_state === 'BROKEN_OUT' && d.age_info?.zone === 'fresh');
  const earlyBreakouts = radarData.filter(d => d.breakout_state === 'BROKEN_OUT' && d.age_info?.zone === 'early');
  const lateBreakouts = radarData.filter(d => d.breakout_state === 'BROKEN_OUT' && d.age_info?.zone === 'late');
  const matureBreakouts = radarData.filter(d => d.breakout_state === 'BROKEN_OUT' && d.age_info?.zone === 'mature');
  const unknownBreakouts = radarData.filter(d => d.breakout_state === 'BROKEN_OUT' && !['fresh', 'early', 'late', 'mature'].includes(d.age_info?.zone));
  
  const ready = radarData.filter(d => d.breakout_state === 'READY_TO_BREAKOUT');
  const consolidating = radarData.filter(d => d.breakout_state === 'CONSOLIDATING');

  const [sortConfig, setSortConfig] = useState<{key: string, direction: 'asc' | 'desc'} | null>(null);

  const requestSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc'; // toggle back
    } else if (sortConfig && sortConfig.key === key) {
      direction = 'desc';
    } else {
      direction = 'desc'; // default to desc for metrics
    }
    setSortConfig({ key, direction });
  };

  const getSortedItems = (items: any[]) => {
    if (!sortConfig) return items;
    return [...items].sort((a, b) => {
      let aVal = a[sortConfig.key];
      let bVal = b[sortConfig.key];
      
      if (sortConfig.key === 'price') {
         aVal = parseFloat(a.close || '0');
         bVal = parseFloat(b.close || '0');
      } else if (sortConfig.key === 'volume') {
         aVal = parseInt(a.volume || '0');
         bVal = parseInt(b.volume || '0');
      } else if (sortConfig.key === 'interest') {
         aVal = (a.holders || 0) + (a.watchers || 0);
         bVal = (b.holders || 0) + (b.watchers || 0);
      }
      
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  };

  const SortIcon = ({ columnKey }: { columnKey: string }) => {
    if (!sortConfig || sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '4px', fontSize: '0.8em' }}>↕</span>;
    return <span style={{ marginLeft: '4px', color: '#60a5fa', fontSize: '0.8em' }}>{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>;
  };

  const renderTable = (items: any[], showAge: boolean = true) => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th onClick={() => requestSort('symbol')} style={{ cursor: 'pointer', userSelect: 'none' }}>Symbol <SortIcon columnKey="symbol" /></th>
            <th onClick={() => requestSort('price')} style={{ cursor: 'pointer', userSelect: 'none' }}>Price <SortIcon columnKey="price" /></th>
            <th onClick={() => requestSort('volume')} style={{ cursor: 'pointer', userSelect: 'none' }}>Volume <SortIcon columnKey="volume" /></th>
            <th>Trend</th>
            <th onClick={() => requestSort('interest')} style={{ cursor: 'pointer', userSelect: 'none' }}>Platform Interest <SortIcon columnKey="interest" /></th>
            {showAge && <th onClick={() => requestSort('breakout_age')} style={{ cursor: 'pointer', userSelect: 'none' }}>Age <SortIcon columnKey="breakout_age" /></th>}
            <th onClick={() => requestSort('radar_priority')} style={{ cursor: 'pointer', userSelect: 'none' }}>Radar Priority <SortIcon columnKey="radar_priority" /></th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {getSortedItems(items).map(item => (
            <tr key={item.symbol} className="clickable-row" onClick={() => onSelectStock(item)}>
              <td className="font-bold">{item.symbol}</td>
              <td>₹{parseFloat(item.close).toLocaleString()}</td>
              <td>{parseInt(item.volume).toLocaleString()}</td>
              <td style={{ color: '#22c55e' }}>{item.ema_50 > item.ema_200 ? 'Bullish Stack' : 'Neutral'}</td>
              <td style={{ color: '#60a5fa' }}>{item.holders} Holders / {item.watchers} Watchers</td>
              {showAge && <td>{item.breakout_age !== null && item.breakout_age !== undefined ? item.breakout_age : '-'}</td>}
              <td style={{ fontWeight: 'bold', color: item.radar_priority > 70 ? '#22c55e' : item.radar_priority > 50 ? '#f59e0b' : '#94a3b8' }}>
                {item.radar_priority ? item.radar_priority.toFixed(1) : '-'}
              </td>
              <td><BreakoutBadge state={item.breakout_state} ageInfo={item.age_info} /></td>
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
        All tracked stocks with breakout classification, sorted by freshness and radar priority.
      </p>

      {radarData.length === 0 ? (
        <div className="empty-state">No stocks in watchlist or portfolio.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
        
          {freshBreakouts.length > 0 && (
            <div style={{ padding: '16px', border: '1px solid #22c55e', borderRadius: '8px', background: 'linear-gradient(180deg, rgba(34,197,94,0.1) 0%, rgba(34,197,94,0) 100%)' }}>
              <h3 style={{ color: '#22c55e', marginBottom: '16px', paddingBottom: '8px', fontSize: '1.2em' }}>
                🔥 Fresh Today (Day 0-1) ({freshBreakouts.length})
              </h3>
              {renderTable(freshBreakouts)}
            </div>
          )}

          {earlyBreakouts.length > 0 && (
            <div>
              <h3 style={{ color: '#10b981', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                📈 Early Continuation (Day 2-3) ({earlyBreakouts.length})
              </h3>
              {renderTable(earlyBreakouts)}
            </div>
          )}

          {lateBreakouts.length > 0 && (
            <div style={{ opacity: 0.8 }}>
              <h3 style={{ color: '#f59e0b', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                ⚠️ Late Entry Zone (Day 4-5) ({lateBreakouts.length})
              </h3>
              {renderTable(lateBreakouts)}
            </div>
          )}

          {(matureBreakouts.length > 0 || unknownBreakouts.length > 0) && (
            <div style={{ opacity: 0.6 }}>
              <h3 style={{ color: '#64748b', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                💤 Mature Breakouts (Day 6+) ({matureBreakouts.length + unknownBreakouts.length})
              </h3>
              {renderTable([...matureBreakouts, ...unknownBreakouts])}
            </div>
          )}

          {ready.length > 0 && (
            <div>
              <h3 style={{ color: '#3b82f6', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
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
              {renderTable(consolidating, false)}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
