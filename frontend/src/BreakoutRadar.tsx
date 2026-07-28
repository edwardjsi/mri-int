import { useState, useEffect, useMemo } from 'react';
import { api } from './api';
import BreakoutBadge from './BreakoutBadge';
import { CaiCandidateReview } from './CaiCandidateReview';

/** Compute the 6 CAS breakout decision gates from radar data. */

/** CAS Breakout Decision Modal — styled like StockDetailsModal. */

type SortCol = 'symbol' | 'close' | 'volume_multiplier' | 'rsi' | 'atr_pct' | 'proximity' | 'mri_score';

const COL_DEFS: { key: SortCol; label: string }[] = [
  { key: 'symbol', label: 'Stock' },
  { key: 'close', label: '₹' },
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
    if (col === 'proximity') { va = a.proximity_to_6m_high ?? -999; vb = b.proximity_to_6m_high ?? -999; }
    else if (col === 'symbol') { va = a.symbol; vb = b.symbol; }
    else if (col === 'volume_multiplier') { va = a.volume_multiplier ?? 0; vb = b.volume_multiplier ?? 0; }
    else { va = (a as any)[col] ?? 0; vb = (b as any)[col] ?? 0; }
    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  });
}



export default function BreakoutRadar({ onViewResearch }: { onViewResearch: (stock: any) => void }) {
  const [stocks, setStocks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState<SortCol>('mri_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [reviewSymbol, setReviewSymbol] = useState<string | null>(null);


  useEffect(() => {
    api.getBreakoutRadar()
      .then((data: any[]) => {
        const enriched = (data || []).map((s: any) => ({
          ...s,
          volume_multiplier: s.avg_volume_20d > 0
            ? Math.round((s.volume / s.avg_volume_20d) * 100) / 100 : 0,
          proximity_to_6m_high: s.rolling_high_6m > 0
            ? Math.round(((s.close / s.rolling_high_6m) - 1) * 10000) / 100 : null,
          atr_pct: s.close > 0
            ? Math.round((s.atr / s.close) * 10000) / 100 : 0,
          mri_score: s.mri_score ?? 0,
        }));
        setStocks(enriched);
      })
      .catch((err: any) => console.error('Radar fetch error:', err))
      .finally(() => setLoading(false));
  }, []);

  const handleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('desc'); }
  };

  const brokenOut = useMemo(() => stocks.filter(d => d.breakout_state === 'BROKEN_OUT'), [stocks]);
  const ready = useMemo(() => stocks.filter(d => d.breakout_state === 'READY_TO_BREAKOUT'), [stocks]);
  const consolidating = useMemo(() => stocks.filter(d => d.breakout_state === 'CONSOLIDATING'), [stocks]);

  const sortedBroken = useMemo(() => sortItems(brokenOut, sortCol, sortDir), [brokenOut, sortCol, sortDir]);
  const sortedReady = useMemo(() => sortItems(ready, sortCol, sortDir), [ready, sortCol, sortDir]);
  const sortedConsolidating = useMemo(() => sortItems(consolidating, sortCol, sortDir), [consolidating, sortCol, sortDir]);

  if (loading) return <div className="loading">Scanning breakout radar…</div>;

  const sortIndicator = (col: SortCol) => {
    if (sortCol !== col) return '';
    return sortDir === 'asc' ? ' ▲' : ' ▼';
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
            <th>CAI</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.symbol} className="clickable-row" onClick={() => onViewResearch(item)}>
              <td className="font-bold"><div>{item.symbol}</div></td>
              <td>₹{parseFloat(String(item.close)).toLocaleString()}</td>
              <td style={{ color: item.volume_multiplier >= 1.3 ? '#22c55e' : '#94a3b8' }}>
                {item.volume_multiplier}x
              </td>
              <td style={{ color: item.rsi > 75 ? '#ef4444' : item.rsi >= 55 ? '#22c55e' : '#f59e0b' }}>
                {item.rsi?.toFixed(1)}
              </td>
              <td>{item.atr_pct?.toFixed(1)}%</td>
              <td style={{ color: item.proximity_to_6m_high !== null && item.proximity_to_6m_high >= -3 ? '#22c55e' : '#94a3b8' }}>
                {item.proximity_to_6m_high !== null ? `${item.proximity_to_6m_high}%` : '—'}
              </td>
              <td style={{ color: item.mri_score >= 80 ? '#22c55e' : item.mri_score >= 60 ? '#f59e0b' : '#ef4444' }}>
                {item.mri_score}
              </td>
              <td><BreakoutBadge state={item.breakout_state} /></td>
              <td>
                <button
                  className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-2 py-1 rounded"
                  onClick={(e) => { e.stopPropagation(); setReviewSymbol(item.symbol); }}
                >
                  Review
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="watchlist">
      <h2 className="section-title">🚀 Breakout Radar</h2>
      <p style={{ color: '#94a3b8', marginBottom: '8px' }}>
        All tracked stocks with breakout status. Click any stock for the 6-gate breakout decision report.
      </p>
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', fontSize: '13px', color: '#64748b' }}>
        <span>🟢 BROKEN: {brokenOut.length}</span>
        <span>🟡 READY: {ready.length}</span>
        <span>⚪ CONSOLIDATING: {consolidating.length}</span>
        <span>📊 Total: {stocks.length}</span>
      </div>

      {stocks.length === 0 ? (
        <div className="empty-state">No breakout stocks found. Add stocks to your watchlist or portfolio.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {brokenOut.length > 0 && (
            <div>
              <h3 style={{ color: '#22c55e', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                🚀 Active Breakouts ({brokenOut.length})
              </h3>
              {renderTable(sortedBroken)}
            </div>
          )}
          {ready.length > 0 && (
            <div>
              <h3 style={{ color: '#f59e0b', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                ⚡ Ready To Breakout ({ready.length})
              </h3>
              {renderTable(sortedReady)}
            </div>
          )}
          {consolidating.length > 0 && (
            <div>
              <h3 style={{ color: '#94a3b8', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                📊 Consolidating ({consolidating.length})
              </h3>
              {renderTable(sortedConsolidating)}
            </div>
          )}
        </div>
      )}

      {reviewSymbol && (
        <div className="fixed inset-0 bg-black/80 z-[100] flex items-center justify-center p-4" onClick={() => setReviewSymbol(null)}>
          <div className="bg-gray-900 w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-gray-700 shadow-2xl" onClick={e => e.stopPropagation()}>
            <CaiCandidateReview symbol={reviewSymbol} onClose={() => setReviewSymbol(null)} />
          </div>
        </div>
      )}
    </div>
  );
}
