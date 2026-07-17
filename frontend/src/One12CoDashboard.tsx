import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from './api';
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
  gate_ema_50_200: boolean;
  gate_ema_200_slope: boolean;
  gate_rs: boolean;
  gate_6m_high: boolean;
  gate_volume: boolean;
  gate_breakout_10d: boolean;
  gate_price_quality: boolean;
  condition_breakout_10d: boolean;
  ema_50: number;
  ema_200: number;
  rs_90d: number;
  last_date: string;
}

type SortCol = 'symbol' | 'close' | 'volume_multiplier' | 'rsi' | 'atr_pct' | 'proximity' | 'mri_score';

const COL_DEFS: { key: SortCol; label: string }[] = [
  { key: 'symbol', label: 'Stock' },
  { key: 'close', label: '₹' },
  { key: 'volume_multiplier', label: 'Vol×' },
  { key: 'rsi', label: 'RSI' },
  { key: 'atr_pct', label: 'ATR%' },
  { key: 'proximity', label: '6m Prox' },
  { key: 'mri_score', label: 'MRI' },
];

/** Build the conditions object that ScoreBreakdown expects from our gate fields. */
function buildConditions(stock: One12CoStock) {
  return {
    ema_50_above_200:      stock.gate_ema_50_200,
    ema_200_slope_positive: stock.gate_ema_200_slope,
    relative_strength:     stock.gate_rs,
    at_6m_high:            stock.gate_6m_high,
    volume_surge:          stock.gate_volume,
    breakout_10d:          stock.gate_breakout_10d,
    price_quality:         stock.gate_price_quality,
  };
}

/** Gateway for the modal — attaches conditions + correct field names. */
function enrichStock(stock: One12CoStock) {
  return {
    ...stock,
    conditions: buildConditions(stock),
    total_score: stock.mri_score,
    score: stock.mri_score,
    current_price: stock.close,
    price: stock.close,
  };
}

function sortItems(items: One12CoStock[], col: SortCol, dir: 'asc' | 'desc'): One12CoStock[] {
  return [...items].sort((a, b) => {
    let va: number | string = 0;
    let vb: number | string = 0;

    if (col === 'proximity') {
      va = a.proximity_to_6m_high ?? -999;
      vb = b.proximity_to_6m_high ?? -999;
    } else if (col === 'symbol') {
      va = a.symbol;
      vb = b.symbol;
    } else {
      va = (a as any)[col] ?? 0;
      vb = (b as any)[col] ?? 0;
    }

    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  });
}

export default function One12CoDashboard({ onViewResearch }: { onViewResearch: (stock: any) => void }) {
  const [stocks, setStocks] = useState<One12CoStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortCol, setSortCol] = useState<SortCol>('mri_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [toast, setToast] = useState<{msg: string; type: string} | null>(null);

  const showToast = useCallback((msg: string, type: string = 'info') => {
    setToast({msg, type});
    setTimeout(() => setToast(null), 3000);
  }, []);

  const fetchStocks = useCallback(() => {
    fetch(`${API_BASE}/api/112co/breakouts`)
      .then(res => res.json())
      .then(data => setStocks(data || []))
      .catch(err => {
        console.error('112Co fetch error:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchStocks(); }, [fetchStocks]);

  const handleSort = (col: SortCol) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(col);
      setSortDir('desc');
    }
  };

  const handleSearch = async (q: string) => {
    setSearchQ(q);
    if (q.length < 2) { setSearchResults([]); return; }
        try {
      const res = await api.search112co(q);
      setSearchResults(res || []);
    } catch { setSearchResults([]); }
    ;  };

  const handleAdd = async (symbol: string) => {
    try {
      const res = await api.add112co(symbol);
      if (res.status === 'already_present') {
        showToast(`${symbol} is already in your list`, 'info');
      } else if (res.status === 'added_with_data') {
        showToast(`${symbol} added to 112Co`, 'success');
        fetchStocks();
      } else if (res.status === 'added_no_data') {
        showToast(`${symbol} added - no price data found`, 'warning');
        fetchStocks();
      } else if (res.status === 'reactivated') {
        showToast(`${symbol} reactivated`, 'success');
        fetchStocks();
      }
    } catch { showToast(`Failed to add ${symbol}`, 'error'); }
    setSearchQ('');
    setSearchResults([]);
  };

  const handleRemove = async (symbol: string) => {
    if (!confirm(`Remove ${symbol} from your 112Co list?`)) return;
    try {
      await api.remove112co(symbol);
      showToast(`${symbol} removed from 112Co`, 'info');
      setStocks(prev => prev.filter(s => s.symbol !== symbol));
    } catch { showToast(`Failed to remove ${symbol}`, 'error'); }
  };

  const brokenOut = useMemo(() => {
    const filtered = stocks.filter(d => d.breakout_state === 'BROKEN_OUT');
    return sortItems(filtered, sortCol, sortDir);
  }, [stocks, sortCol, sortDir]);

  const ready = useMemo(() => {
    const filtered = stocks.filter(d => d.breakout_state === 'READY_TO_BREAKOUT');
    return sortItems(filtered, sortCol, sortDir);
  }, [stocks, sortCol, sortDir]);

  const consolidating = useMemo(() => {
    const filtered = stocks.filter(d => d.breakout_state === 'CONSOLIDATING');
    return sortItems(filtered, sortCol, sortDir);
  }, [stocks, sortCol, sortDir]);

  const noData = useMemo(() => {
    return stocks.filter(d => d.breakout_state === 'MISSING');
  }, [stocks]);

  if (loading) return <div className="loading">Scanning 112Co universe…</div>;
  if (error) return <div className="error-state">⚠️ Failed to load: {error}</div>;

  const sortIndicator = (col: SortCol) => {
    if (sortCol !== col) return '';
    return sortDir === 'asc' ? ' ▲' : ' ▼';
  };

  const renderTable = (items: One12CoStock[]) => (
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
            <tr key={item.symbol} className="clickable-row" onClick={() => onViewResearch(item)}>
              <td className="font-bold">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>{item.symbol}</span>
                  <button onClick={e => { e.stopPropagation(); handleRemove(item.symbol); }}
                    style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '12px', padding: '0', opacity: '0.5' }}
                    title="Remove from 112Co">×</button>
                </div>
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
      {toast && (
        <div style={{
          position: 'fixed', top: '20px', right: '20px', zIndex: 10000,
          padding: '12px 20px', borderRadius: '8px', fontSize: '13px',
          background: toast.type === 'success' ? '#22c55e' : toast.type === 'warning' ? '#f59e0b' : toast.type === 'error' ? '#ef4444' : '#334155',
          color: 'white', fontWeight: 600, boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        }}>{toast.msg}</div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h2 className="section-title" style={{ margin: 0 }}>🔬 112Co Breakout Radar</h2>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            placeholder="+ Add stock by symbol..."
            value={searchQ}
            onChange={e => handleSearch(e.target.value)}
            style={{
              padding: '8px 12px', borderRadius: '6px', border: '1px solid #334155',
              background: '#1e293b', color: '#e2e8f0', fontSize: '13px',
              width: '220px', outline: 'none'
            }}
          />
          {searchResults.length > 0 && (
            <div style={{
              position: 'absolute', top: '100%', right: 0, zIndex: 999,
              background: '#1e293b', border: '1px solid #334155', borderRadius: '6px',
              width: '300px', maxHeight: '300px', overflowY: 'auto', marginTop: '4px'
            }}>
              {searchResults.map((r: any) => (
                <div key={r.symbol}
                  style={{
                    padding: '8px 12px', cursor: 'pointer', fontSize: '12px',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    borderBottom: '1px solid #1e293b'
                  }}
                  onClick={() => handleAdd(r.symbol)}
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#e2e8f0' }}>{r.symbol}</div>
                    {r.stock_name && <div style={{ fontSize: '10px', color: '#64748b' }}>{r.stock_name}</div>}
                  </div>
                  <div style={{
                    fontSize: '10px', padding: '2px 8px', borderRadius: '4px',
                    background: r.in_universe ? '#22c55e20' : '#3b82f620',
                    color: r.in_universe ? '#22c55e' : '#3b82f6'
                  }}>{r.in_universe ? '✓ In list' : '+ Add'}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <p style={{ color: '#94a3b8', marginBottom: '8px' }}>
        Click any stock for the full 7-gate breakdown + fundamentals. Hover the × to remove.
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

          {noData.length > 0 && (
            <div>
              <h3 style={{ color: '#64748b', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
                ❌ No Data ({noData.length})
              </h3>
              <p style={{ color: '#64748b', fontSize: '12px', marginBottom: '8px' }}>
                These symbols don't have price data on Yahoo Finance.
              </p>
              {renderTable(noData)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
