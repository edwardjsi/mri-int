import { useState, useEffect, useMemo } from 'react';
import { apiFetch } from './api';

/**
 * ConvictionEngine — Cross-list management integrity dashboard.
 * Decision 097. Surfaces verdict zones + lag tracking across Digital Twin
 * holdings and the 112 Co Universe, sorted worst-first by default.
 */


interface ConvictionRow {
  symbol: string;
  sources: string[];
  accuracy_pct: number;
  trend: string;
  total_promises: number;
  achieved_count: number;
  missed_count: number;
  avg_variance_pct: number | null;
  consecutive_miss_quarters: number;
  lag_score: number;
  current_verdict: string;
  previous_verdict: string | null;
  verdict_flipped: boolean;
  last_verdict_flip: string | null;
  last_updated: string | null;
}

interface ConvictionSummary {
  total: number;
  'ADD ZONE': number;
  'HOLD ZONE': number;
  'REDUCE ZONE': number;
  'THESIS BROKEN': number;
  WATCHING: number;
  lagging_count: number;
  flipped_count: number;
}

interface ConvictionResponse {
  source: string;
  summary: ConvictionSummary;
  rows: ConvictionRow[];
}

const VERDICT_COLORS: Record<string, { bg: string; fg: string }> = {
  'ADD ZONE':      { bg: '#14532d', fg: '#4ade80' },
  'HOLD ZONE':     { bg: '#451a03', fg: '#fbbf24' },
  'REDUCE ZONE':   { bg: '#7f1d1d', fg: '#f87171' },
  'THESIS BROKEN': { bg: '#500',    fg: '#fff'    },
  'WATCHING':      { bg: '#1e293b', fg: '#94a3b8' },
};

const SOURCE_LABELS: Record<string, string> = {
  digital_twin: '📊 Digital Twin',
  watchlist:    '⭐ Watchlist',
  '112co':      '🚀 112 Co',
};

type SortKey = 'symbol' | 'accuracy_pct' | 'lag_score' | 'consecutive_miss_quarters' | 'total_promises' | 'last_verdict_flip';
type SortDir = 'asc' | 'desc';

export default function ConvictionEngine({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [data, setData] = useState<ConvictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<'all' | 'digital_twin' | '112co' | 'watchlist'>('all');
  const [verdictFilter, setVerdictFilter] = useState<string>('any');
  const [sortKey, setSortKey] = useState<SortKey>('accuracy_pct');
  const [sortDir, setSortDir] = useState<SortDir>('asc'); // worst-first by default

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const url = `/guidance/conviction?source=${source}&verdict=${encodeURIComponent(verdictFilter)}&limit=200`;
    apiFetch(url)
      .then((d: ConvictionResponse) => { if (!cancelled) setData(d); })
      .catch(err => {
        if (!cancelled) {
          console.error('ConvictionEngine fetch error:', err);
          setError(err.message || 'Failed to load');
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [source, verdictFilter]);

  const sortedRows = useMemo(() => {
    if (!data) return [];
    const rows = [...data.rows];
    rows.sort((a, b) => {
      const va = a[sortKey] ?? '';
      const vb = b[sortKey] ?? '';
      let cmp = 0;
      if (typeof va === 'number' && typeof vb === 'number') {
        cmp = va - vb;
      } else if (va < vb) cmp = -1;
      else if (va > vb) cmp = 1;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return rows;
  }, [data, sortKey, sortDir]);

  const handleSort = (k: SortKey) => {
    if (sortKey === k) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(k);
      // Sensible defaults: numeric/date columns descending first, symbol ascending
      setSortDir(k === 'symbol' ? 'asc' : 'desc');
    }
  };

  const sortArrow = (k: SortKey) =>
    sortKey === k ? (sortDir === 'asc' ? ' ↑' : ' ↓') : '';

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1400, margin: '0 auto', color: '#e2e8f0', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <header style={{ marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 700, color: '#f8fafc' }}>
          🧠 Conviction Engine
        </h1>
        <p style={{ margin: '6px 0 0', color: '#94a3b8', fontSize: '0.95rem' }}>
          Management integrity across your Digital Twin holdings and the 112 Co Universe.
          Sorted worst-first — these are the names most likely to break your thesis.
        </p>
      </header>

      {/* Source filter chips */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        {(['all', 'digital_twin', '112co', 'watchlist'] as const).map(s => (
          <button
            key={s}
            onClick={() => setSource(s)}
            style={{
              padding: '6px 14px',
              borderRadius: 20,
              border: '1px solid #334155',
              background: source === s ? '#1e40af' : '#0f172a',
              color: source === s ? '#fff' : '#cbd5e1',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              letterSpacing: '0.03em',
            }}
          >
            {s === 'all' ? 'All Sources' : SOURCE_LABELS[s]}
          </button>
        ))}
      </div>

      {/* Verdict filter chips */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 18, flexWrap: 'wrap' }}>
        {['any', 'ADD ZONE', 'HOLD ZONE', 'REDUCE ZONE', 'THESIS BROKEN', 'WATCHING'].map(v => {
          const c = VERDICT_COLORS[v];
          const active = verdictFilter === v;
          return (
            <button
              key={v}
              onClick={() => setVerdictFilter(v)}
              style={{
                padding: '5px 12px',
                borderRadius: 16,
                border: `1px solid ${active ? (c?.fg || '#64748b') : '#334155'}`,
                background: active ? (c?.bg || '#1e293b') : '#0f172a',
                color: active ? (c?.fg || '#fff') : '#94a3b8',
                fontSize: '0.72rem',
                fontWeight: 700,
                cursor: 'pointer',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              {v}
            </button>
          );
        })}
      </div>

      {/* Summary cards */}
      {data?.summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 20 }}>
          {(['ADD ZONE', 'HOLD ZONE', 'REDUCE ZONE', 'THESIS BROKEN', 'WATCHING'] as const).map(zone => {
            const c = VERDICT_COLORS[zone];
            return (
              <div
                key={zone}
                style={{
                  background: '#0f172a',
                  border: `1px solid ${c.bg}`,
                  borderLeft: `4px solid ${c.fg}`,
                  borderRadius: 8,
                  padding: '12px 14px',
                }}
              >
                <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
                  {zone}
                </div>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: c.fg, marginTop: 4 }}>
                  {data.summary[zone] ?? 0}
                </div>
              </div>
            );
          })}
          <div style={{ background: '#0f172a', border: '1px solid #7f1d1d', borderLeft: '4px solid #f87171', borderRadius: 8, padding: '12px 14px' }}>
            <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
              Lagging (≥2q)
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f87171', marginTop: 4 }}>
              {data.summary.lagging_count}
            </div>
          </div>
          <div style={{ background: '#0f172a', border: '1px solid #1e3a8a', borderLeft: '4px solid #60a5fa', borderRadius: 8, padding: '12px 14px' }}>
            <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
              Verdict Flipped
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#60a5fa', marginTop: 4 }}>
              {data.summary.flipped_count}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div style={{ padding: 14, background: '#7f1d1d', borderRadius: 8, color: '#fff', marginBottom: 16 }}>
          Error loading: {error}
        </div>
      )}

      {loading && (
        <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>
          Loading conviction data…
        </div>
      )}

      {!loading && sortedRows.length === 0 && (
        <div style={{ padding: 40, textAlign: 'center', color: '#64748b', background: '#0f172a', borderRadius: 8 }}>
          No companies match the current filter.
          {data?.summary?.total === 0 && (
            <div style={{ marginTop: 8, fontSize: '0.85rem' }}>
              The credibility table needs at least one verified promise per stock — run the priming pipeline first.
            </div>
          )}
        </div>
      )}

      {!loading && sortedRows.length > 0 && (
        <div style={{ background: '#0f172a', borderRadius: 8, overflow: 'hidden', border: '1px solid #1e293b' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: '#1e293b', textAlign: 'left' }}>
                {([
                  ['symbol', 'Symbol'],
                  ['accuracy_pct', 'Accuracy'],
                  ['total_promises', 'Promises'],
                  ['lag_score', 'Lag Score'],
                  ['consecutive_miss_quarters', 'Streak'],
                  ['last_verdict_flip', 'Last Flip'],
                ] as [SortKey, string][]).map(([k, label]) => (
                  <th
                    key={k}
                    onClick={() => handleSort(k)}
                    style={{
                      padding: '10px 14px',
                      cursor: 'pointer',
                      userSelect: 'none',
                      color: '#cbd5e1',
                      fontWeight: 700,
                      fontSize: '0.72rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                      borderBottom: '1px solid #334155',
                    }}
                  >
                    {label}{sortArrow(k)}
                  </th>
                ))}
                <th style={{ padding: '10px 14px', color: '#cbd5e1', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em', borderBottom: '1px solid #334155' }}>
                  Sources
                </th>
                <th style={{ padding: '10px 14px', color: '#cbd5e1', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em', borderBottom: '1px solid #334155' }}>
                  Verdict
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map(row => {
                const c = VERDICT_COLORS[row.current_verdict] || VERDICT_COLORS['WATCHING'];
                return (
                  <tr
                    key={row.symbol}
                    onClick={() => onSelectStock({ symbol: row.symbol })}
                    style={{ borderBottom: '1px solid #1e293b', cursor: 'pointer' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#1e293b')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '10px 14px', fontWeight: 700, color: '#f8fafc' }}>
                      {row.symbol}
                      {row.verdict_flipped && (
                        <span style={{ marginLeft: 6, fontSize: '0.65rem', padding: '2px 6px', borderRadius: 8, background: '#1e3a8a', color: '#60a5fa', fontWeight: 700 }}>
                          FLIP
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '10px 14px', color: row.accuracy_pct >= 60 ? '#4ade80' : row.accuracy_pct >= 40 ? '#fbbf24' : '#f87171', fontWeight: 700 }}>
                      {row.accuracy_pct.toFixed(1)}%
                    </td>
                    <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                      {row.achieved_count}/{row.total_promises}
                      <span style={{ color: '#475569', marginLeft: 6, fontSize: '0.75rem' }}>
                        ({row.missed_count}❌)
                      </span>
                    </td>
                    <td style={{ padding: '10px 14px', color: row.lag_score >= 50 ? '#f87171' : row.lag_score > 0 ? '#fbbf24' : '#4ade80', fontWeight: 700 }}>
                      {row.lag_score.toFixed(0)}
                    </td>
                    <td style={{ padding: '10px 14px', color: row.consecutive_miss_quarters >= 2 ? '#f87171' : '#cbd5e1' }}>
                      {row.consecutive_miss_quarters}q
                    </td>
                    <td style={{ padding: '10px 14px', color: '#94a3b8', fontSize: '0.78rem' }}>
                      {row.last_verdict_flip || '—'}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      {row.sources.map(s => (
                        <span
                          key={s}
                          style={{
                            marginRight: 4,
                            padding: '2px 8px',
                            borderRadius: 10,
                            background: '#1e293b',
                            color: '#94a3b8',
                            fontSize: '0.68rem',
                            fontWeight: 600,
                          }}
                        >
                          {SOURCE_LABELS[s] || s}
                        </span>
                      ))}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <span style={{
                        background: c.bg,
                        color: c.fg,
                        fontWeight: 700,
                        fontSize: '0.7rem',
                        padding: '4px 10px',
                        borderRadius: 16,
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        display: 'inline-block',
                      }}>
                        {row.current_verdict}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <footer style={{ marginTop: 16, fontSize: '0.72rem', color: '#475569', textAlign: 'center' }}>
        Verdict zones · ADD ≥75% (stable trend) · HOLD ≥60% · REDUCE ≥40% · THESIS BROKEN &lt;40% · WATCHING &lt;3 promises<br />
        Lag score = consecutive miss quarters / total verified quarters × 100. Streak resets on any ACHIEVED/PARTIAL.
      </footer>
    </div>
  );
}
