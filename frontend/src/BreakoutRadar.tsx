import { useState, useEffect, useMemo } from 'react';
import { api } from './api';
import BreakoutBadge from './BreakoutBadge';

/** Compute the 6 CAS breakout decision gates from radar data. */
function buildCasGates(s: any) {
  const volMultiplier = s.avg_volume_20d > 0 ? s.volume / s.avg_volume_20d : 0;
  const passDecision = (s.decision_score ?? 0) >= 85;
  const passMri = (s.mri_score ?? 0) >= 80;
  const passWeeklyResistance = !!s.weekly_close_above_resistance;
  const passVolume = volMultiplier >= 1.3;
  const passAge = s.breakout_age !== null && s.breakout_age !== undefined && s.breakout_age <= 15;
  const passConfidence = (s.confidence ?? 0) >= 0.8;
  const passed = [passDecision, passMri, passWeeklyResistance, passVolume, passAge, passConfidence].filter(Boolean).length;

  return {
    gates: [
      { label: '1. Decision Score \u2265 85',      pass: passDecision,     detail: `${s.decision_score ?? '?'}/85` },
      { label: '2. MRI Technical \u2265 80',         pass: passMri,          detail: `${s.mri_score ?? '?'}/80` },
      { label: '3. Weekly Close > Resistance',       pass: passWeeklyResistance },
      { label: '4. Volume \u2265 1.3\u00d7 Avg',     pass: passVolume,       detail: `${volMultiplier.toFixed(2)}\u00d7` },
      { label: '5. Breakout Age \u2264 15d',          pass: passAge,          detail: s.breakout_age != null ? `${s.breakout_age}d` : '--' },
      { label: '6. Confidence \u2265 80%',            pass: passConfidence,   detail: `${((s.confidence ?? 0) * 100).toFixed(0)}%` },
    ],
    passed,
    total: 6,
    volMultiplier,
  };
}

/** CAS Breakout Decision Modal — styled like StockDetailsModal. */
function CasBreakoutModal({ stock, onClose }: { stock: any; onClose: () => void }) {
  const cas = buildCasGates(stock);

  if (!stock) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h3 className="modal-title" style={{ marginBottom: '4px' }}>{stock.symbol}</h3>
            <BreakoutBadge state={stock.breakout_state} />
            <div className="card-meta">Breakout Decision Report</div>
          </div>
          <button className="link-btn" onClick={onClose} style={{ fontSize: '24px' }}>&times;</button>
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '16px', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>CAS Score</div>
            <div style={{
              fontSize: '28px', fontWeight: 900,
              color: (stock.decision_score ?? 0) >= 85 ? '#22c55e' : '#f59e0b'
            }}>
              {stock.decision_score?.toFixed(1) ?? '--'}
            </div>
          </div>
          <div style={{ width: '1px', height: '40px', background: '#334155' }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Gates Passed</div>
            <div style={{
              fontSize: '28px', fontWeight: 900,
              color: cas.passed >= 4 ? '#22c55e' : '#ef4444'
            }}>
              {cas.passed}/{cas.total}
            </div>
          </div>
          <div style={{ width: '1px', height: '40px', background: '#334155' }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Price</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#e2e8f0' }}>
              \u20b9{parseFloat(String(stock.close)).toLocaleString()}
            </div>
          </div>
        </div>

        <div style={{ marginTop: '1.5rem' }}>
          <h4 style={{ marginBottom: '12px', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            \ud83d\uded2 6-Gate Breakout Decision
          </h4>
          <div className="conditions-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            {cas.gates.map((g, i) => (
              <div key={i} className="condition-item" style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px' }}>
                <div className="condition-label" style={{ fontSize: '11px' }}>
                  {g.label}
                  {g.detail && <div style={{ fontSize: '9px', color: '#64748b' }}>{g.detail}</div>}
                </div>
                <div className={'condition-value ' + (g.pass ? 'condition-pass' : 'condition-fail')}
                     style={{ fontSize: '10px', marginTop: '4px' }}>
                  {g.pass ? '\u2705 PASS' : '\u274c FAIL'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {cas.passed < 4 && (
          <div style={{ marginTop: '1.5rem', padding: '12px', borderRadius: '8px',
                        background: '#1e293b', border: '1px solid #334155' }}>
            <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 700, marginBottom: '6px' }}>
              \ud83d\udca1 What needs to improve
            </div>
            {cas.gates.filter(g => !g.pass).map((g, i) => (
              <div key={i} style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '2px' }}>
                \u2022 {g.label} \u2014 currently FAILED
              </div>
            ))}
          </div>
        )}

        <div className="modal-actions" style={{ marginTop: '1.5rem', display: 'flex', gap: '10px' }}>
          <button className="btn-secondary" onClick={onClose} style={{ flex: 1 }}>Close Report</button>
        </div>
      </div>
    </div>
  );
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
    if (col === 'proximity') { va = a.proximity_to_6m_high ?? -999; vb = b.proximity_to_6m_high ?? -999; }
    else if (col === 'symbol') { va = a.symbol; vb = b.symbol; }
    else if (col === 'volume_multiplier') { va = a.volume_multiplier ?? 0; vb = b.volume_multiplier ?? 0; }
    else { va = (a as any)[col] ?? 0; vb = (b as any)[col] ?? 0; }
    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  });
}

export default function BreakoutRadar({ onSelectStock: _onSelectStock }: { onSelectStock?: (stock: any) => void } = {}) {
  const [stocks, setStocks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState<SortCol>('mri_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [casStock, setCasStock] = useState<any>(null);

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
            <tr key={item.symbol} className="clickable-row" onClick={() => setCasStock(item)}>
              <td className="font-bold"><div>{item.symbol}</div></td>
              <td>\u20b9{parseFloat(String(item.close)).toLocaleString()}</td>
              <td style={{ color: item.volume_multiplier >= 1.3 ? '#22c55e' : '#94a3b8' }}>
                {item.volume_multiplier}x
              </td>
              <td style={{ color: item.rsi > 75 ? '#ef4444' : item.rsi >= 55 ? '#22c55e' : '#f59e0b' }}>
                {item.rsi?.toFixed(1)}
              </td>
              <td>{item.atr_pct?.toFixed(1)}%</td>
              <td style={{ color: item.proximity_to_6m_high !== null && item.proximity_to_6m_high >= -3 ? '#22c55e' : '#94a3b8' }}>
                {item.proximity_to_6m_high !== null ? `${item.proximity_to_6m_high}%` : '\u2014'}
              </td>
              <td style={{ color: item.mri_score >= 80 ? '#22c55e' : item.mri_score >= 60 ? '#f59e0b' : '#ef4444' }}>
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
        All tracked stocks with breakout status. Click any stock for the 6-gate breakout decision report.
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

      {casStock && (
        <CasBreakoutModal stock={casStock} onClose={() => setCasStock(null)} />
      )}
    </div>
  );
}
