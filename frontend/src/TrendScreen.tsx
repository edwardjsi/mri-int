import { useState, useEffect, useMemo } from 'react';
import { api } from './api';

type SortCol = 'symbol' | 'close' | 'ema_10' | 'ema_50' | 'ema_200' | 'rolling_high_52w' | 'market_cap_cr' | 'mri_score';

const COL_DEFS: { key: SortCol; label: string }[] = [
  { key: 'symbol', label: 'Stock' },
  { key: 'close', label: '\u20b9' },
  { key: 'ema_10', label: 'EMA10' },
  { key: 'ema_50', label: 'EMA50' },
  { key: 'ema_200', label: 'EMA200' },
  { key: 'rolling_high_52w', label: '52w High' },
  { key: 'market_cap_cr', label: 'Mkt Cap (Cr)' },
  { key: 'mri_score', label: 'MRI' },
];

function sortItems(items: any[], col: SortCol, dir: 'asc' | 'desc'): any[] {
  return [...items].sort((a, b) => {
    let va: number | string = 0;
    let vb: number | string = 0;
    if (col === 'symbol') { va = a.symbol; vb = b.symbol; }
    else { va = (a as any)[col] ?? 0; vb = (b as any)[col] ?? 0; }
    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  });
}

export default function TrendScreen({ onViewResearch }: { onViewResearch: (stock: any) => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortCol, setSortCol] = useState<SortCol>('mri_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    api.getTrendScreen()
      .then((res: any) => {
        setData(res);
      })
      .catch((err: any) => {
        console.error('Trend screen fetch error:', err);
        setError(err.message || 'Failed to load trend screen');
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('desc'); }
  };

  const sortedResults = useMemo(() => {
    if (!data?.results) return [];
    return sortItems(data.results, sortCol, sortDir);
  }, [data, sortCol, sortDir]);

  const sortIndicator = (col: SortCol) => {
    if (sortCol !== col) return '';
    return sortDir === 'asc' ? ' \u25b2' : ' \u25bc';
  };

  if (loading) return <div className="loading">Scanning trend screen\u2026</div>;
  if (error) return <div className="error-state">Error: {error}</div>;
  if (!data) return <div className="empty-state">No data returned from trend screen.</div>;

  return (
    <div className="watchlist">
      <h2 className="section-title">\ud83d\udcca Trend Screen</h2>
      <p style={{ color: '#94a3b8', marginBottom: '8px' }}>
        Stocks passing all 7 filters: multi-EMA uptrend alignment, market cap 1,000\u201375,000 Cr, within 25% of 52-week high.
      </p>
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', fontSize: '13px', color: '#64748b' }}>
        <span>\ud83c\udfaf Matches: {data.count}</span>
        {!data.results?.[0]?.market_cap_cr && (
          <span style={{ color: '#f59e0b' }}>\u26a0\ufe0f Market cap data unavailable \u2014 excluding cap filters</span>
        )}
      </div>

      {data.results?.length > 0 ? (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                {COL_DEFS.map(c => (
                  <th key={c.key} onClick={() => handleSort(c.key)} style={{ cursor: 'pointer', userSelect: 'none' }}>
                    {c.label}{sortIndicator(c.key)}
                  </th>
                ))}
                <th>State</th>
                <th>MOSI</th>
              </tr>
            </thead>
            <tbody>
              {sortedResults.map((item: any) => {
                const mosi = item.mosi_lite_score ?? 0;
                return (
                  <tr key={item.symbol} className="clickable-row" onClick={() => onViewResearch(item)}>
                    <td className="font-bold"><div>{item.symbol}</div></td>
                    <td>\u20b9{parseFloat(String(item.close)).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                    <td style={{ color: item.ema_10 && item.close > item.ema_10 ? '#22c55e' : '#ef4444' }}>
                      {item.ema_10 ? `\u20b9${parseFloat(String(item.ema_10)).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '\u2014'}
                    </td>
                    <td style={{ color: item.ema_50 && item.close > item.ema_50 ? '#22c55e' : '#ef4444' }}>
                      {item.ema_50 ? `\u20b9${parseFloat(String(item.ema_50)).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '\u2014'}
                    </td>
                    <td style={{ color: item.ema_200 && item.close > item.ema_200 ? '#22c55e' : '#ef4444' }}>
                      {item.ema_200 ? `\u20b9${parseFloat(String(item.ema_200)).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '\u2014'}
                    </td>
                    <td>{item.rolling_high_52w ? `\u20b9${parseFloat(String(item.rolling_high_52w)).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '\u2014'}</td>
                    <td>{item.market_cap_cr ? `\u20b9${parseFloat(String(item.market_cap_cr)).toLocaleString('en-IN')}` : '\u2014'}</td>
                    <td style={{ color: item.mri_score >= 80 ? '#22c55e' : item.mri_score >= 60 ? '#f59e0b' : '#ef4444' }}>
                      {item.mri_score}
                    </td>
                    <td style={{ fontSize: '12px' }}>{item.breakout_state || '\u2014'}</td>
                    <td>
                      <span style={{ color: mosi >= 70 ? '#22c55e' : mosi >= 50 ? '#f59e0b' : '#94a3b8', fontSize: '13px' }}>
                        {mosi.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">No stocks passed all 7 filters today.</div>
      )}
    </div>
  );
}
