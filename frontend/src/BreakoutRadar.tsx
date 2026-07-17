import { useState, useEffect, useMemo } from 'react';
import { api } from './api';
import BreakoutBadge from './BreakoutBadge';

/** Map gate fields to the conditions object that ScoreBreakdown expects. */
function buildConditions(stock: any) {
  return {
    ema_50_above_200:      !!stock.gate_ema_50_200,
    ema_200_slope_positive: !!stock.gate_ema_200_slope,
    relative_strength:     !!stock.gate_rs,
    at_6m_high:            !!stock.gate_6m_high,
    volume_surge:          !!stock.gate_volume,
    breakout_10d:          !!stock.gate_breakout_10d,
    price_quality:         !!stock.gate_price_quality,
  };
}

/** Attach conditions + score so StockDetailsModal shows the 7-gate breakdown. */
function enrichStock(stock: any) {
  return {
    ...stock,
    conditions: buildConditions(stock),
    total_score: stock.mri_score ?? stock.total_score ?? 0,
    score: stock.mri_score ?? stock.total_score ?? 0,
    current_price: stock.close,
    price: stock.close,
  };
}

type SortCol = 'symbol' | 'close' | 'volume_multiplier' | 'rsi' | 'atr_pct' | 'proximity' | 'mri_score';

const COL_DEFS: { key: SortCol; label: string }[] = [
  { key: 'symbol', label: 'Stock' },
  { key: 'close', label: '\u20b9' },
  { key: 'volume_multiplier', label: 'Vol\u00d7' },
  { key: 'rsi', label: 'RSI' },
  { key: 'atr_pct', label: 'ATR%' },
  { key: 'proximity', label: '6m Prox' },
  { key: 'mri_score', label: 'MRI' },
];

function sortItems(items: any[], col: SortCol, dir: 'asc' | 'desc'): any[] {
  return [...items].sort((a, b) => {
    let va: number | string = 0;
    let vb: number | string = 0;

    if (col === 'proximity') {
      va = a.proximity_to_6m_high ?? -999;
      vb = b.proximity_to_6m_high ?? -999;
    } else if (col === 'symbol') {
      va = a.symbol;
      vb = b.symbol;
    } else if (col === 'volume_multiplier') {
      va = a.volume_multiplier ?? 0;
      vb = b.volume_multiplier ?? 0;
    } else {
      va = (a as any)[col] ?? 0;
      vb = (b as any)[col] ?? 0;
    }

    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  });
}

export default function BreakoutRadar({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [stocks, setStocks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState<SortCol>('mri_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    api.getBreakoutRadar()
      .then((data: any[]) => {
        const enriched = (data || []).map((s: any) => ({
          ...s,
          volume_multiplier: s.avg_volume_20d > 0
            ? Math.round((s.volume / s.avg_volume_20d) * 100) / 100
            : 0,
          proximity_to_6m_high: s.rolling_high_6m > 0
            ? Math.round(((s.close / s.rolling_high_6m) - 1) * 10000) / 100
            : null,
          atr_pct: s.close > 0
            ? Math.round((s.atr / s.close) * 10000) / 100
            : 0,
          mri_score: s.mri_score ?? 0,
        }));
        setStocks(enriched);
      })
      .catch((err: any) => console.error('Radar fetch error:', err))
      .finally(() => setLoading(false));
  }, []);

  const handleSort = (col: SortCol) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(col);
      setSortDir('desc');
    }
  };

  const brokenOut = useMemo(() => stocks.filter(d => d.breakout_state === 'BROKEN_OUT'), [stocks]);
  const ready = useMemo(() => stocks.filter(d => d.breakout_state === 'READY_TO_BREAKOUT'), [stocks]);
  const consolidating = useMemo(() => stocks.filter(d => d.breakout_state === 'CONSOLIDATING'), [stocks]);

  const sortedBroken = useMemo(() => sortItems(brokenOut, sortCol, sortDir), [brokenOut, sortCol, sortDir]);
  const sortedReady = useMemo(() => sortItems(ready, sortCol, sortDir), [ready, sortCol, sortDir]);
  const sortedConsolidating = useMemo(() => sortItems(consolidating, sortCol, sortDir), [consolidating, sortCol, sortDir]);

  if (loading) return <div className="loading">Scanning breakout radar\u2026</div>;

  const sortIndicator = (col: SortCol) => {
    if (sortCol !== col) return '';
    return sortDir === 'asc' ? ' \u25b2' : ' \u25bc';
  };

  const renderTable = (items: any[]) => (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            {COL_DEFS.map(c => (
              <th key={c.key} onClick={() => handleSort(c.key)} style={{ cursor: 'pointer', userSelect: 'none' }}>
                {c.label}{sortIndicator(c.key)}
              </th>
            ))}
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.symbol} className="clickable-row" onClick={() => onSelectStock(enrichStock(item))}>
              <td className="font-bold">
                <div>{item.symbol}</div>
              </td>
              <td>\u20b9{parseFloat(String(item.close)).toLocaleString()}</td>
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
      <h2 className="section-title">\ud83d\ude80 Breakout Radar</h2>
      <p style={{ color: '#94a3b8', marginBottom: '8px' }}>
        All watchlist, portfolio, and breakout-discovery stocks \u2014 sorted by breakout status.
        Click any stock for the full 7-gate breakdown.
      </p>
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', fontSize: '13px', color: '#64748b' }}>
        <span>\ud83d\udfe2 BROKEN: {brokenOut.length}</span>
        <span>\ud83d\udfe1 READY: {ready.length}</span>
        <span>\u26aa CONSOLIDATING: {consolidating.length}</span>
        <span>\ud83d\udcca Total: {stocks.length}</span>
      </div>

      {stocks.length === 0 ? (
        <div className="empty-state">No breakout stocks found. Add stocks to your watchlist or portfolio.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {brokenOut.length > 0 && (
            <div>
              <h3 style={{ color: '#22c55e', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                \ud83d\ude80 Active Breakouts ({brokenOut.length})
              </h3>
              {renderTable(sortedBroken)}
            </div>
          )}
          {ready.length > 0 && (
            <div>
              <h3 style={{ color: '#f59e0b', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                \u26a1 Ready To Breakout ({ready.length})
              </h3>
              {renderTable(sortedReady)}
            </div>
          )}
          {consolidating.length > 0 && (
            <div>
              <h3 style={{ color: '#94a3b8', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                \ud83d\udcca Consolidating ({consolidating.length})
              </h3>
              {renderTable(sortedConsolidating)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
