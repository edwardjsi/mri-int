// Updated: 2026-04-24
// @ts-nocheck
import { useState, useEffect } from 'react';
import { api } from './api';

interface AdminMetrics {
  total_users: number;
  active_watchlists: number;
  active_portfolios: number;
  last_ingestion: string | null;
}

interface DataHealth {
  total_symbols: number;
  null_indicators: number;
  suspicious_rs: number;
  stale_indicators: number;
  coverage_pct: number;
  last_price_date: string | null;
  last_score_date: string | null;
  last_regime_date: string | null;
  drift_days: number;
}

interface SymbolGrade {
  symbol: string;
  total_score: number | null;
  last_score_date: string | null;
  interest_count: number; // How many users track/hold this
}

export default function AdminDashboard({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [health, setHealth] = useState<DataHealth | null>(null);
  const [topStocks, setTopStocks] = useState<{ top_watched: any[], top_held: any[] } | null>(null);
  const [dailyLeaderboard, setDailyLeaderboard] = useState<{ date: string | null, top_stocks: any[] }>({ date: null, top_stocks: [] });
  const [hallOfFame, setHallOfFame] = useState<any[]>([]);
  const [strategyShadow, setStrategyShadow] = useState<any[]>([]);
  const [globalUniverse, setGlobalUniverse] = useState<any[]>([]);
  const [swingTrades, setSwingTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRecovering, setIsRecovering] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [qualityLeaderboard, setQualityLeaderboard] = useState<any[]>([]);
  const [topQualityStocks, setTopQualityStocks] = useState<any[]>([]);
  const [auditingSymbol, setAuditingSymbol] = useState<string | null>(null);
  const [auditStatus, setAuditStatus] = useState<{ symbol: string; msg: string } | null>(null);
  const [aaeCandidates, setAaeCandidates] = useState<any[]>([]);
  const [pnlLedger, setPnlLedger] = useState<any>(null);

  // Sorting states
  const [leaderboardSort, setLeaderboardSort] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'total_score', direction: 'desc' });
  const [explorerSort, setGlobalSort] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'total_interest', direction: 'desc' });
  const [qifSort, setQifSort] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'score', direction: 'desc' });
  const [shadowSort, setShadowSort] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'perf_pct', direction: 'desc' });
  const [swingSort, setSwingSort] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'entry_date', direction: 'desc' });
  const [hofSort, setHofSort] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'perf_pct', direction: 'desc' });

  const handleLeaderboardSort = (key: string) => {
    setLeaderboardSort(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const handleExplorerSort = (key: string) => {
    setGlobalSort(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const applySort = (arr: any[], sort: { key: string, direction: 'asc' | 'desc' }) =>
    [...arr].sort((a, b) => {
      const aVal = a[sort.key], bVal = b[sort.key];
      if (aVal == null) return sort.direction === 'asc' ? 1 : -1;
      if (bVal == null) return sort.direction === 'asc' ? -1 : 1;
      if (aVal === bVal) return 0;
      const res = aVal < bVal ? -1 : 1;
      return sort.direction === 'asc' ? res : -res;
    });

  const handleQifSort = (key: string) => setQifSort(prev => ({ key, direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc' }));
  const handleShadowSort = (key: string) => setShadowSort(prev => ({ key, direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc' }));
  const handleSwingSort = (key: string) => setSwingSort(prev => ({ key, direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc' }));
  const handleHofSort = (key: string) => setHofSort(prev => ({ key, direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc' }));

  const sortIcon = (key: string, sort: { key: string, direction: 'asc' | 'desc' }) =>
    sort.key === key ? (sort.direction === 'asc' ? '🔼' : '🔽') : '↕️';

  // Regime Status Indicator
  const [regimeStatus, setRegimeStatus] = useState<{ regime: string; date: string } | null>(null);

  useEffect(() => {
    api.getRegime().then(d => setRegimeStatus(d)).catch(() => {});
  }, []);

  const getRegimeColor = (regime: string) => {
    if (regime === 'BULLISH') return { bg: '#22c55e', text: 'white' };
    if (regime === 'SIDEWAYS') return { bg: '#eab308', text: 'black' };
    return { bg: '#ef4444', text: 'white' }; // BEARISH
  };

  const sortedLeaderboard = [...dailyLeaderboard.top_stocks].sort((a, b) => {
    const { key, direction } = leaderboardSort;
    let aVal = a[key];
    let bVal = b[key];
    if (key === 'close') { aVal = a.close; bVal = b.close; }
    
    if (aVal === bVal) return 0;
    const res = aVal < bVal ? -1 : 1;
    return direction === 'asc' ? res : -res;
  });

  const sortedExplorer = globalUniverse
    .filter(s => s.symbol.toLowerCase().includes(searchTerm.toLowerCase()))
    .sort((a, b) => {
      const { key, direction } = explorerSort;
      let aVal = a[key];
      let bVal = b[key];
      
      if (aVal === bVal) return 0;
      const res = aVal < bVal ? -1 : 1;
      return direction === 'asc' ? res : -res;
    });

  const loadAdminIntel = async () => {
    setLoading(true);
    setError('');

    // Decoupled fetching: Total Dashboard Failure is now avoided if one service is slow
    const fetchMetrics = async () => {
      try { const data = await api.getAdminMetrics(); setMetrics(data); }
      catch (e) { console.error('Metrics failed', e); }
    };
    const fetchHealth = async () => {
      try { const data = await api.getAdminDataHealth(); setHealth(data); }
      catch (e) { console.error('Health failed', e); }
    };
    const fetchTop = async () => {
      try { const data = await api.getAdminTopStocks(); setTopStocks(data); }
      catch (e) { console.error('Top stocks failed', e); }
    };
    const fetchGlobal = async () => {
      try { const data = await api.getAdminGlobalUniverse(); setGlobalUniverse(data); }
      catch (e) { console.error('Global universe failed', e); setError('Global list is taking longer than expected...'); }
    };
    const fetchLeaderboard = async () => {
      try { const data = await api.getAdminDailyLeaderboard(); setDailyLeaderboard(data); }
      catch (e) { console.error('Leaderboard failed', e); }
    };
    const fetchHallOfFame = async () => {
      try { const data = await api.getAdminHallOfFame(); setHallOfFame(data); }
      catch (e) { console.error('Hall of Fame failed', e); }
    };
    const fetchShadow = async () => {
      try { const data = await api.getAdminStrategyShadow(); setStrategyShadow(data); }
      catch (e) { console.error('Strategy Shadow failed', e); }
    };
    const fetchSwingTrades = async () => {
      try { const data = await api.getAdminSwingTrades(); setSwingTrades(data); }
      catch (e) { console.error('Swing trades failed', e); }
    };
    const fetchAuditLogs = async () => {
      try { const data = await api.getAdminAuditLogs(); setAuditLogs(data); }
      catch (e) { console.error('Audit logs failed', e); }
    };
    const fetchQualityLeaderboard = async () => {
      try { const data = await api.getTopImprovers(30); setQualityLeaderboard(data); }
      catch (e) { console.error('Quality leaderboard failed', e); }
    };
    const fetchTopQuality = async () => {
      try { const data = await api.getTopQualityStocks(6); setTopQualityStocks(data); }
      catch (e) { console.error('Top quality stocks failed', e); }
    };
    const fetchAae = async () => {
      try { const data = await api.getAaeTopCandidates(); setAaeCandidates(data); }
      catch (e) { console.error('AAE failed', e); }
    };
    const fetchPnl = async () => {
      try { const data = await api.getAdminPnlLedger(); setPnlLedger(data); }
      catch (e) { console.error('P&L Ledger failed', e); }
    };

    await Promise.allSettled([
      fetchMetrics(), fetchTop(), fetchGlobal(), fetchLeaderboard(), 
      fetchHallOfFame(), fetchShadow(), fetchHealth(), fetchSwingTrades(),
      fetchAuditLogs(), fetchQualityLeaderboard(), fetchTopQuality(), fetchAae(), fetchPnl()
    ]);
    setLoading(false);
  };

  const handleTriggerRecovery = async () => {
    if (!confirm('This will trigger a background indicator recompute for all missing symbols. Proceed?')) return;
    setIsRecovering(true);
    try {
      await api.triggerAdminRecovery();
      alert('Recovery task started. Check back in a few minutes.');
    } catch (e) {
      alert('Failed to trigger recovery: ' + e.message);
    } finally {
      setIsRecovering(false);
    }
  };

  const handleTriggerPipeline = async () => {
    if (!confirm('This will run the FULL pipeline: ingest → indicators → regime → signals → STEE → emails → QIF. This takes 5-10 minutes. Proceed?')) return;
    setIsRecovering(true);
    try {
      await api.triggerPipeline();
      alert('Full pipeline started! Check back in 5-10 minutes for updated data.');
    } catch (e) {
      alert('Failed to trigger pipeline: ' + e.message);
    } finally {
      setIsRecovering(false);
    }
  };

  const handleAddGlobalSymbol = async () => {
    if (!newSymbol) return;
    try {
      await api.addGlobalSymbol(newSymbol);
      alert(`${newSymbol} added to global tracking.`);
      setNewSymbol('');
      loadAdminIntel(); // Refresh explorer
    } catch (e) {
      alert('Failed to add symbol: ' + e.message);
    }
  };

const handleRepairSymbol = async (e: React.MouseEvent, symbol: string) => {
  e.stopPropagation(); // Don't trigger row click/select
  if (!confirm(`SURGICAL REPAIR: This will DELETE all price/score history for ${symbol} and re-fetch it fresh. Proceed?`)) return;
  try {
    await api.repairSymbol(symbol);
    alert(`${symbol} data cleared. It will re-appear after the next background ingestion cycle.`);
    loadAdminIntel();
  } catch (e) {
    alert('Failed to trigger repair: ' + e.message);
  }
};

  const handleAudit = async (e: React.MouseEvent, symbol: string) => {
    e.stopPropagation();
    if (!confirm(`Run full 10-Layer AAE Forensic Audit for ${symbol}? Results will be emailed to you.`)) return;
    setAuditingSymbol(symbol);
    try {
      const result = await api.triggerAaeReport(symbol);
      setAuditStatus({ symbol, msg: result.message || 'Audit started — check your email shortly.' });
    } catch (err: any) {
      alert('Audit failed: ' + err.message);
    } finally {
      setAuditingSymbol(null);
    }
  };

  useEffect(() => {
    loadAdminIntel();
  }, []);

  // Combined unique symbols for the "Global Explorer"
  const filteredSymbols = globalUniverse.filter(s => 
    s.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading && !metrics) return <div className="loading">📡 Gathering intelligence...</div>;

  return (
    <div className="admin-dashboard">
      <div className="stats-row">
        <div className="stat-card" style={{ background: regimeStatus ? `linear-gradient(135deg, ${getRegimeColor(regimeStatus.regime).bg}22 0%, #1e293b 100%)` : '', border: regimeStatus ? `1px solid ${getRegimeColor(regimeStatus.regime).bg}` : '' }}>
          <div className="stat-label" style={{ color: regimeStatus ? getRegimeColor(regimeStatus.regime).text : '' }}>
            🛡️ Market Regime
          </div>
          <div className="stat-value" style={{ fontSize: '1.4rem', fontWeight: 900, color: regimeStatus ? getRegimeColor(regimeStatus.regime).text : '' }}>
            {regimeStatus?.regime || '...'}
          </div>
          <div className="stat-subtitle" style={{ fontSize: '10px', opacity: 0.7 }}>
            {regimeStatus?.date || ''}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Platform Users</div>
          <div className="stat-value">{metrics?.total_users}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Digital Twins Active</div>
          <div className="stat-value">{metrics?.active_portfolios || 0}</div>
        </div>
        <div className="stat-card">
            <div className="stat-label">Indicator Coverage</div>
            <div className={`stat-value ${(health?.coverage_pct || 100) < 95 ? 'status-critical' : ''}`} style={{ fontSize: '1.2rem' }}>
                {health ? `${health.coverage_pct}%` : '...'}
            </div>
            <div className="stat-subtitle" style={{ fontSize: '10px', opacity: 0.7 }}>
                {health?.null_indicators} missing
            </div>
        </div>
        <div className="stat-card">
            <div className="stat-label">Market Freshness</div>
            <div className={`stat-value ${health?.drift_days && health.drift_days > 1 ? 'status-critical' : ''}`} style={{ fontSize: '1.2rem' }}>
                {health?.last_price_date || 'Pending'}
            </div>
            <div className="stat-subtitle" style={{ fontSize: '10px', opacity: 0.7 }}>
                Drift: {health?.drift_days || 0}d
            </div>
        </div>
        <div className="stat-card">
            <div className="stat-label">Data Integrity</div>
            <div className={`stat-value ${(health?.suspicious_rs || 0) > 0 || (health?.stale_indicators || 0) > 0 ? 'status-critical' : ''}`} style={{ fontSize: '1.2rem' }}>
                {health ? `${health.suspicious_rs + health.stale_indicators === 0 ? 'CLEAN' : 'WARNING'}` : '...'}
            </div>
            <div className="stat-subtitle" style={{ fontSize: '10px', opacity: 0.7 }}>
                {health?.suspicious_rs} RS gaps | {health?.stale_indicators} stale
            </div>
        </div>
        <div className="stat-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <button 
                onClick={handleTriggerRecovery} 
                disabled={isRecovering}
                className="action-btn btn-primary"
                style={{ width: '48%', height: '100%', fontSize: '0.9rem' }}
            >
                {isRecovering ? '⏳ Repairing...' : '🛠️ Force Repair'}
            </button>
            <div style={{ width: '4%' }}></div>
<button 
                onClick={handleTriggerPipeline} 
                disabled={isRecovering}
                className="action-btn btn-executed"
                style={{ width: '48%', height: '100%', fontSize: '0.9rem' }}
            >
                {isRecovering ? '⏳ Running...' : '🚀 Run Pipeline'}
            </button>
        </div>
      </div>

      {error && <div className="error-alert">{error}</div>}

      {/* P&L Ledger */}
      {pnlLedger?.summary && (
        <section className="section" style={{ marginTop: '24px' }}>
          <h3 className="section-title">💰 Live P&L Ledger</h3>
          <p className="section-subtitle">Realized performance across all manual positions and STEE swing trades.</p>
          <div className="stats-row" style={{ marginTop: '12px' }}>
            <div className="stat-card" style={{ background: 'linear-gradient(135deg, #064e3b22 0%, #1e293b 100%)' }}>
              <div className="stat-label">Total Closed Trades</div>
              <div className="stat-value">{pnlLedger.summary.total_closed_trades}</div>
            </div>
            <div className="stat-card" style={{ background: pnlLedger.summary.win_rate_pct >= 50 ? 'linear-gradient(135deg, #22c55e22 0%, #1e293b 100%)' : 'linear-gradient(135deg, #ef444422 0%, #1e293b 100%)' }}>
              <div className="stat-label">Win Rate</div>
              <div className="stat-value" style={{ color: pnlLedger.summary.win_rate_pct >= 50 ? '#22c55e' : '#ef4444' }}>
                {pnlLedger.summary.win_rate_pct}%
              </div>
              <div className="stat-subtitle">{pnlLedger.summary.winning_trades}W / {pnlLedger.summary.losing_trades}L</div>
            </div>
            <div className="stat-card" style={{ background: pnlLedger.summary.total_realized_pnl >= 0 ? 'linear-gradient(135deg, #22c55e22 0%, #1e293b 100%)' : 'linear-gradient(135deg, #ef444422 0%, #1e293b 100%)' }}>
              <div className="stat-label">Total Realized P&L</div>
              <div className="stat-value" style={{ color: pnlLedger.summary.total_realized_pnl >= 0 ? '#22c55e' : '#ef4444', fontSize: '1.2rem' }}>
                ₹{pnlLedger.summary.total_realized_pnl?.toLocaleString()}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg Return / Trade</div>
              <div className="stat-value" style={{ color: pnlLedger.summary.avg_return_pct >= 0 ? '#22c55e' : '#ef4444', fontSize: '1.2rem' }}>
                {pnlLedger.summary.avg_return_pct >= 0 ? '+' : ''}{pnlLedger.summary.avg_return_pct}%
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Largest Win</div>
              <div className="stat-value" style={{ color: '#22c55e', fontSize: '1rem' }}>+{pnlLedger.summary.largest_win_pct}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Largest Loss</div>
              <div className="stat-value" style={{ color: '#ef4444', fontSize: '1rem' }}>{pnlLedger.summary.largest_loss_pct}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Open Positions</div>
              <div className="stat-value">{pnlLedger.summary.open_positions}</div>
            </div>
          </div>
          {pnlLedger.closed_trades?.length > 0 && (
            <div className="table-container" style={{ marginTop: '16px' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Entry Date</th>
                    <th>Entry</th>
                    <th>Exit Date</th>
                    <th>Exit</th>
                    <th>Return %</th>
                    <th>P&L (₹)</th>
                  </tr>
                </thead>
                <tbody>
                  {pnlLedger.closed_trades.slice(0, 20).map((t: any, i: number) => (
                    <tr key={i}>
                      <td className="font-bold">{t.symbol}</td>
                      <td><span className={`action-badge ${t.trade_type === 'STEE' ? 'badge-executed' : ''}`}>{t.trade_type}</span></td>
                      <td>{t.entry_date ? new Date(t.entry_date).toLocaleDateString() : '-'}</td>
                      <td>₹{t.entry_price?.toLocaleString()}</td>
                      <td>{t.exit_date ? new Date(t.exit_date).toLocaleDateString() : '-'}</td>
                      <td>₹{t.exit_price?.toLocaleString()}</td>
                      <td style={{ color: (t.return_pct || 0) >= 0 ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                        {t.return_pct >= 0 ? '+' : ''}{t.return_pct}%
                      </td>
                      <td style={{ color: (t.pnl_abs || 0) >= 0 ? '#22c55e' : '#ef4444' }}>
                        ₹{t.pnl_abs?.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <section className="section" style={{ marginTop: '24px' }}>
        <div style={{
          background: 'linear-gradient(135deg, rgba(88, 28, 135, 0.28) 0%, rgba(15, 23, 42, 0.92) 55%, rgba(30, 41, 59, 0.92) 100%)',
          border: '1px solid rgba(192, 132, 252, 0.22)',
          borderRadius: '18px',
          padding: '18px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: '16px', flexWrap: 'wrap', marginBottom: '16px' }}>
            <div>
              <div style={{ fontSize: '11px', letterSpacing: '0.12em', textTransform: 'uppercase', color: '#c084fc', fontWeight: 800 }}>
                Latest Intelligence Layer
              </div>
              <h3 className="section-title" style={{ margin: '6px 0 0 0' }}>QIF + Trajectory Snapshot</h3>
              <p className="section-subtitle" style={{ marginTop: '8px', maxWidth: '760px' }}>
                This is the newest admin dashboard layer from the Quality Investor Framework: top compounders on one side, fastest improvers on the other.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <div style={{ padding: '10px 12px', borderRadius: '12px', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(148, 163, 184, 0.16)' }}>
                <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>Top Quality</div>
                <div style={{ fontSize: '20px', fontWeight: 800, color: '#f8fafc' }}>{topQualityStocks.length}</div>
              </div>
              <div style={{ padding: '10px 12px', borderRadius: '12px', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(148, 163, 184, 0.16)' }}>
                <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>Fast Improvers</div>
                <div style={{ fontSize: '20px', fontWeight: 800, color: '#f8fafc' }}>{qualityLeaderboard.length}</div>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.58)', border: '1px solid rgba(148, 163, 184, 0.14)', borderRadius: '14px', padding: '14px' }}>
              <div style={{ fontSize: '12px', color: '#e9d5ff', fontWeight: 700, marginBottom: '10px' }}>Top Quality Compounders</div>
              {topQualityStocks.length > 0 ? (
                <div style={{ display: 'grid', gap: '10px' }}>
                  {topQualityStocks.slice(0, 4).map((stock: any) => (
                    <button
                      key={`top-quality-${stock.symbol}`}
                      onClick={() => onSelectStock({ ...stock, symbol: stock.symbol })}
                      style={{
                        textAlign: 'left',
                        background: 'rgba(30, 41, 59, 0.78)',
                        border: '1px solid rgba(192, 132, 252, 0.18)',
                        borderRadius: '12px',
                        padding: '12px',
                        color: '#f8fafc',
                        cursor: 'pointer'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                        <span style={{ fontWeight: 800 }}>{stock.symbol}</span>
                        <span style={{ fontWeight: 800, color: '#86efac' }}>{parseFloat(stock.score || 0).toFixed(1)}</span>
                      </div>
                      <div style={{ marginTop: '6px', fontSize: '11px', color: '#cbd5e1' }}>{stock.category || 'HIGH_QUALITY'}</div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="empty-state" style={{ padding: '18px 8px' }}>No top-quality data yet. Step 7 needs to populate `quality_verdicts`.</div>
              )}
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.58)', border: '1px solid rgba(148, 163, 184, 0.14)', borderRadius: '14px', padding: '14px' }}>
              <div style={{ fontSize: '12px', color: '#e9d5ff', fontWeight: 700, marginBottom: '10px' }}>Fastest Improvers</div>
              {qualityLeaderboard.length > 0 ? (
                <div style={{ display: 'grid', gap: '10px' }}>
                  {qualityLeaderboard.slice(0, 4).map((stock: any) => (
                    <button
                      key={`quality-improver-${stock.symbol}`}
                      onClick={() => onSelectStock({ ...stock, symbol: stock.symbol })}
                      style={{
                        textAlign: 'left',
                        background: 'rgba(30, 41, 59, 0.78)',
                        border: '1px solid rgba(192, 132, 252, 0.18)',
                        borderRadius: '12px',
                        padding: '12px',
                        color: '#f8fafc',
                        cursor: 'pointer'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                        <span style={{ fontWeight: 800 }}>{stock.symbol}</span>
                        <span style={{ fontWeight: 800, color: stock.score_change >= 0 ? '#86efac' : '#fca5a5' }}>
                          {stock.score_change >= 0 ? '+' : ''}{parseFloat(stock.score_change || 0).toFixed(1)}
                        </span>
                      </div>
                      <div style={{ marginTop: '6px', fontSize: '11px', color: '#cbd5e1' }}>
                        Velocity {parseFloat(stock.velocity || 0).toFixed(2)} • {stock.category || 'WATCHLIST'}
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="empty-state" style={{ padding: '18px 8px' }}>No improver data yet. The admin page is live, but the newest trajectory feed is still empty.</div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="section" style={{ marginTop: '24px' }}>
        <div style={{
          background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(15, 23, 42, 0.95) 100%)',
          border: '1px solid rgba(34, 197, 94, 0.3)',
          borderRadius: '18px',
          padding: '24px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 className="section-title" style={{ margin: 0, color: '#86efac' }}>🚀 AAE V3: Active Alpha Candidates</h3>
              <p className="section-subtitle" style={{ color: '#94a3b8' }}>
                Institutional Rerating Engine: Detecting high-conviction structural inflections.
              </p>
            </div>
            <div className="badge-executed" style={{ padding: '4px 12px', fontSize: '12px' }}>Operational</div>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            {aaeCandidates.length > 0 ? aaeCandidates.map(c => (
              <div key={c.symbol} style={{ 
                background: 'rgba(30, 41, 59, 0.5)', 
                border: '1px solid rgba(148, 163, 184, 0.1)', 
                borderRadius: '12px', 
                padding: '16px',
                cursor: 'pointer',
                transition: 'transform 0.2s'
              }} onClick={() => onSelectStock(c)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 800, fontSize: '1.1rem' }}>{c.symbol}</span>
                  <span style={{ color: '#86efac', fontWeight: 900, fontSize: '1.2rem' }}>{c.master_score}</span>
                </div>
                <div style={{ fontSize: '11px', color: '#cbd5e1', marginBottom: '10px', display: 'flex', justifyContent: 'space-between' }}>
                   <span>{c.sector}</span>
                   <span style={{ opacity: 0.7 }}>{c.valuation_status}</span>
                </div>
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                  {c.reasons?.slice(0, 2).map((r, i) => (
                    <span key={i} style={{ 
                      fontSize: '9px', 
                      background: 'rgba(51, 65, 85, 0.8)', 
                      padding: '2px 8px', 
                      borderRadius: '4px',
                      border: '1px solid rgba(148, 163, 184, 0.1)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '100%'
                    }} title={r}>
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            )) : (
              <div className="empty-state" style={{ gridColumn: '1 / -1', padding: '24px' }}>
                Analyzing institutional candidates...
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="section" style={{ marginTop: '24px' }}>
        <h3 className="section-title">🏆 Daily Leaderboard ({dailyLeaderboard.date})</h3>
        <p className="section-subtitle">Top scoring stocks from today's quantitative analysis.</p>
        <div className="table-container" style={{ marginTop: '16px' }}>
            <table className="data-table">
                <thead>
                    <tr>
                        <th onClick={() => handleLeaderboardSort('symbol')} style={{ cursor: 'pointer' }}>Symbol {leaderboardSort.key === 'symbol' ? (leaderboardSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th onClick={() => handleLeaderboardSort('total_score')} style={{ cursor: 'pointer' }}>Score {leaderboardSort.key === 'total_score' ? (leaderboardSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th onClick={() => handleLeaderboardSort('close')} style={{ cursor: 'pointer' }}>Price {leaderboardSort.key === 'close' ? (leaderboardSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th>Breakdown (EMA | Slope | RS | High | Vol)</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedLeaderboard.map(s => {
                        const conditions = {
                            ema_50_above_200: s.condition_ema_50_200,
                            ema_200_slope_positive: s.condition_ema_200_slope,
                            at_6m_high: s.condition_6m_high,
                            volume_surge: s.condition_volume,
                            relative_strength: s.condition_rs,
                            breakout_10d: s.condition_breakout_10d,
                            price_quality: s.condition_price_quality
                        };
                        return (
                            <tr key={s.symbol} onClick={() => onSelectStock({ ...s, conditions, score: s.total_score, price: s.close })} className="clickable-row">
                                <td className="font-bold">{s.symbol}</td>
                                <td><span className="score-badge">{s.total_score}</span></td>
                                <td>₹{s.close?.toLocaleString()}</td>
                                <td>
                                    <div style={{ display: 'flex', gap: '8px', fontSize: '12px' }}>
                                        <span style={{ color: s.condition_ema_50_200 ? '#22c55e' : '#64748b' }}>{s.condition_ema_50_200 ? '✅' : '❌'}</span>
                                        <span style={{ color: s.condition_ema_200_slope ? '#22c55e' : '#64748b' }}>{s.condition_ema_200_slope ? '✅' : '❌'}</span>
                                        <span style={{ color: s.condition_rs ? '#22c55e' : '#64748b' }}>{s.condition_rs ? '✅' : '❌'}</span>
                                        <span style={{ color: s.condition_6m_high ? '#22c55e' : '#64748b' }}>{s.condition_6m_high ? '✅' : '❌'}</span>
                                        <span style={{ color: s.condition_volume ? '#22c55e' : '#64748b' }}>{s.condition_volume ? '✅' : '❌'}</span>
                                    </div>
                                </td>
                            </tr>
                        );
                    })}
                    {(!dailyLeaderboard.top_stocks.length) && (
                        <tr><td colSpan={4} className="empty-state">No leaderboard data found for today.</td></tr>
                    )}
                </tbody>
            </table>
        </div>
      </section>

      <section className="section" style={{ marginTop: '24px' }}>
        <h3 className="section-title">💎 Fundamental Quality Leaderboard (QIF)</h3>
        <p className="section-subtitle">Top-rated business quality verdicts from the institutional framework.</p>
        {auditStatus && (
          <div style={{
            marginTop: '10px', padding: '10px 14px', borderRadius: '8px',
            background: '#22c55e20', border: '1px solid #22c55e40', color: '#86efac',
            fontSize: '12px', fontWeight: 600
          }}>
            🔬 Audit queued for <b>{auditStatus.symbol}</b> — {auditStatus.msg}
            <button onClick={() => setAuditStatus(null)} style={{ marginLeft: '12px', background: 'none', border: 'none', color: '#86efac', cursor: 'pointer', fontSize: '12px' }}>✕</button>
          </div>
        )}
        <div className="table-container" style={{ marginTop: '16px' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => handleQifSort('symbol')} style={{ cursor: 'pointer' }}>Symbol {sortIcon('symbol', qifSort)}</th>
                <th onClick={() => handleQifSort('score')} style={{ cursor: 'pointer' }}>Verdict {sortIcon('score', qifSort)}</th>
                <th onClick={() => handleQifSort('score')} style={{ cursor: 'pointer' }}>Score {sortIcon('score', qifSort)}</th>
                <th onClick={() => handleQifSort('score_change')} style={{ cursor: 'pointer' }}>Change {sortIcon('score_change', qifSort)}</th>
                <th onClick={() => handleQifSort('velocity')} style={{ cursor: 'pointer' }}>Velocity {sortIcon('velocity', qifSort)}</th>
                <th>Trend</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {applySort(qualityLeaderboard, qifSort).map(s => (
                <tr key={s.symbol + '_qif'} onClick={() => onSelectStock({ ...s, symbol: s.symbol })} className="clickable-row">
                  <td className="font-bold">{s.symbol}</td>
                  <td>
                    <span style={{ 
                      padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold',
                      background: (s.score >= 80 ? '#22c55e' : (s.score >= 70 ? '#a855f7' : (s.score >= 60 ? '#eab308' : '#ef4444'))) + '20',
                      color: (s.score >= 80 ? '#22c55e' : (s.score >= 70 ? '#a855f7' : (s.score >= 60 ? '#eab308' : '#ef4444'))),
                      border: `1px solid ${s.score >= 80 ? '#22c55e' : (s.score >= 70 ? '#a855f7' : (s.score >= 60 ? '#eab308' : '#ef4444'))}40`
                    }}>
                      {s.category}
                    </span>
                  </td>
                  <td><span className="score-badge">{parseFloat(s.score).toFixed(1)}</span></td>
                  <td>
                    <span style={{ color: s.score_change >= 0 ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                      {s.score_change >= 0 ? '+' : ''}{parseFloat(s.score_change).toFixed(1)}
                    </span>
                  </td>
                  <td>{parseFloat(s.velocity || 0).toFixed(2)}</td>
                  <td>{s.score_change > 5 ? '🚀 BREAKOUT' : (s.velocity > 2 ? '📈 IMPROVING' : 'STABLE')}</td>
                  <td>
                    <button
                      onClick={(e) => handleAudit(e, s.symbol)}
                      disabled={auditingSymbol === s.symbol}
                      style={{
                        background: auditingSymbol === s.symbol ? '#64748b' : '#3b82f6',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '3px 10px',
                        fontSize: '11px',
                        cursor: auditingSymbol === s.symbol ? 'not-allowed' : 'pointer',
                        fontWeight: 700,
                      }}
                    >
                      {auditingSymbol === s.symbol ? '⏳...' : '🤖 AAE Audit'}
                    </button>
                  </td>
                </tr>
              ))}
              {(!qualityLeaderboard.length) && (
                <tr><td colSpan={7} className="empty-state">No quality analysis data found. Run Step 7.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section" style={{ marginTop: '24px' }}>
        <h3 className="section-title">🕵️ Strategy Shadow Tracker</h3>
        <p className="section-subtitle">What the Top 10 looks like today (ignores Market Regime filters).</p>
        <div className="table-container" style={{ marginTop: '16px' }}>
            <table className="data-table">
<thead>
            <tr>
              <th onClick={() => handleShadowSort('symbol')} style={{ cursor: 'pointer' }}>Symbol {sortIcon('symbol', shadowSort)}</th>
              <th onClick={() => handleShadowSort('first_entry_date')} style={{ cursor: 'pointer' }}>First Entered {sortIcon('first_entry_date', shadowSort)}</th>
              <th onClick={() => handleShadowSort('is_active')} style={{ cursor: 'pointer' }}>Status {sortIcon('is_active', shadowSort)}</th>
              <th onClick={() => handleShadowSort('entry_price')} style={{ cursor: 'pointer' }}>Entry Price {sortIcon('entry_price', shadowSort)}</th>
              <th onClick={() => handleShadowSort('latest_price')} style={{ cursor: 'pointer' }}>Current Price {sortIcon('latest_price', shadowSort)}</th>
              <th onClick={() => handleShadowSort('perf_pct')} style={{ cursor: 'pointer' }}>Total Return % {sortIcon('perf_pct', shadowSort)}</th>
            </tr>
          </thead>
          <tbody>
            {applySort(strategyShadow, shadowSort).map(s => (
                        <tr key={s.symbol} style={!s.is_active ? { opacity: 0.6 } : {}}>
                            <td className="font-bold">{s.symbol}</td>
                            <td>{new Date(s.first_entry_date).toLocaleDateString()}</td>
                            <td>
                                <span className={`action-badge ${s.is_active ? 'badge-executed' : 'badge-skipped'}`}>
                                    {s.is_active ? 'ACTIVE' : 'DROPPED'}
                                </span>
                            </td>
                            <td>₹{s.entry_price?.toLocaleString()}</td>
                            <td>₹{s.latest_price?.toLocaleString()}</td>
                            <td style={{ color: (s.perf_pct || 0) >= 0 ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                                {s.perf_pct >= 0 ? '+' : ''}{s.perf_pct}%
                            </td>
                        </tr>
                    ))}
                    {(!strategyShadow.length) && (
                        <tr><td colSpan={6} className="empty-state">No shadow strategy data yet.</td></tr>
                    )}
                </tbody>
            </table>
        </div>
      </section>

      <section className="section" style={{ marginTop: '24px' }}>
        <h3 className="section-title">🚀 STEE Active Swing Trades</h3>
        <p className="section-subtitle">Real-time tracking of automated momentum breakout trades.</p>
<div className="table-container" style={{ marginTop: '16px' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => handleSwingSort('client_name')} style={{ cursor: 'pointer' }}>Client {sortIcon('client_name', swingSort)}</th>
                  <th onClick={() => handleSwingSort('symbol')} style={{ cursor: 'pointer' }}>Symbol {sortIcon('symbol', swingSort)}</th>
                  <th onClick={() => handleSwingSort('entry_date')} style={{ cursor: 'pointer' }}>Entry Date {sortIcon('entry_date', swingSort)}</th>
<th onClick={() => handleSwingSort('entry_price')} style={{ cursor: 'pointer' }}>Entry Price {sortIcon('entry_price', swingSort)}</th>
              <th>Stop Loss</th>
              <th onClick={() => handleSwingSort('current_price')} style={{ cursor: 'pointer' }}>Current Price {sortIcon('current_price', swingSort)}</th>
              <th onClick={() => handleSwingSort('quantity')} style={{ cursor: 'pointer' }}>Qty {sortIcon('quantity', swingSort)}</th>
              <th onClick={() => handleSwingSort('pnl_abs')} style={{ cursor: 'pointer' }}>PnL (₹) {sortIcon('pnl_abs', swingSort)}</th>
              <th onClick={() => handleSwingSort('perf_pct')} style={{ cursor: 'pointer' }}>Perf % {sortIcon('perf_pct', swingSort)}</th>
              <th onClick={() => handleSwingSort('status')} style={{ cursor: 'pointer' }}>Status {sortIcon('status', swingSort)}</th>
            </tr>
                </thead>
                <tbody>
                    {applySort(swingTrades, swingSort).map(t => (
                        <tr key={t.id}>
                            <td className="text-xs opacity-70">{t.client_name}</td>
                            <td className="font-bold">{t.symbol}</td>
                            <td>{new Date(t.entry_date).toLocaleDateString()}</td>
                            <td>₹{t.entry_price?.toLocaleString()}</td>
                            <td style={{ color: '#ef4444' }}>₹{t.stop_loss?.toLocaleString()}</td>
                            <td>₹{t.current_price?.toLocaleString()}</td>
                            <td>{t.quantity}</td>
                            <td style={{ color: (t.pnl_abs || 0) >= 0 ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                                ₹{t.pnl_abs?.toLocaleString()}
                            </td>
                            <td style={{ color: (t.perf_pct || 0) >= 0 ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                                {t.perf_pct >= 0 ? '+' : ''}{t.perf_pct}%
                            </td>
                            <td>
                                <span className={`action-badge ${t.status === 'OPEN' ? 'badge-executed' : t.status === 'PARTIAL_EXIT' ? 'badge-skipped' : ''}`}>
                                    {t.status}
                                </span>
                            </td>
                        </tr>
                    ))}
                    {(!swingTrades.length) && (
                        <tr><td colSpan={10} className="empty-state">No active swing trades found.</td></tr>
                    )}
                </tbody>
            </table>
        </div>
      </section>

      <section className="section" style={{ marginTop: '24px' }}>
        <h3 className="section-title">🏛️ Hall of Fame (High Score Performance)</h3>
        <p className="section-subtitle">Tracking stocks from their first 75+ score appearance in MRI.</p>
        <div className="table-container" style={{ marginTop: '16px' }}>
            <table className="data-table">
<thead>
            <tr>
              <th onClick={() => handleHofSort('symbol')} style={{ cursor: 'pointer' }}>Symbol {sortIcon('symbol', hofSort)}</th>
              <th onClick={() => handleHofSort('first_appeared_date')} style={{ cursor: 'pointer' }}>First Seen {sortIcon('first_appeared_date', hofSort)}</th>
              <th onClick={() => handleHofSort('entry_price')} style={{ cursor: 'pointer' }}>Entry Price {sortIcon('entry_price', hofSort)}</th>
              <th onClick={() => handleHofSort('latest_price')} style={{ cursor: 'pointer' }}>Current Price {sortIcon('latest_price', hofSort)}</th>
              <th onClick={() => handleHofSort('perf_pct')} style={{ cursor: 'pointer' }}>Perf % {sortIcon('perf_pct', hofSort)}</th>
              <th onClick={() => handleHofSort('max_score')} style={{ cursor: 'pointer' }}>Max Score {sortIcon('max_score', hofSort)}</th>
            </tr>
          </thead>
<tbody>
            {applySort(hallOfFame, hofSort).map(s => (
              <tr key={s.symbol}>
                            <td className="font-bold">{s.symbol}</td>
                            <td>{new Date(s.first_appeared_date).toLocaleDateString()}</td>
                            <td>₹{s.entry_price?.toLocaleString()}</td>
                            <td>₹{s.latest_price?.toLocaleString()}</td>
                            <td style={{ color: (s.perf_pct || 0) >= 0 ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                                {s.perf_pct >= 0 ? '+' : ''}{s.perf_pct}%
                            </td>
                            <td><span className="score-badge">{s.max_score}</span></td>
                        </tr>
                    ))}
                    {(!hallOfFame.length) && (
                        <tr><td colSpan={6} className="empty-state">No Hall of Fame data yet.</td></tr>
                    )}
                </tbody>
            </table>
        </div>
      </section>

      <section className="section" style={{ marginTop: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 className="section-title" style={{ margin: 0 }}>🌍 Global Symbol Explorer</h3>
            <input 
                type="text" 
                placeholder="Search symbol..." 
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="form-input" 
                style={{ width: '200px', marginBottom: 0, padding: '6px 12px' }}
            />
        </div>
        <p className="section-subtitle">Deduplicated view of stocks added by all users (Anonymized).</p>
        
        <div className="table-container" style={{ marginTop: '16px', maxHeight: '300px', overflowY: 'auto' }}>
            <table className="data-table">
                <thead>
                    <tr>
                        <th onClick={() => handleExplorerSort('symbol')} style={{ cursor: 'pointer' }}>Symbol {explorerSort.key === 'symbol' ? (explorerSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th onClick={() => handleExplorerSort('is_breakout')} style={{ cursor: 'pointer' }}>Breakout {explorerSort.key === 'is_breakout' ? (explorerSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th onClick={() => handleExplorerSort('score')} style={{ cursor: 'pointer' }}>Score {explorerSort.key === 'score' ? (explorerSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th onClick={() => handleExplorerSort('rs_90d')} style={{ cursor: 'pointer' }}>RS {explorerSort.key === 'rs_90d' ? (explorerSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th>Price</th>
                        <th onClick={() => handleExplorerSort('watchers')} style={{ cursor: 'pointer' }}>Watchers {explorerSort.key === 'watchers' ? (explorerSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th onClick={() => handleExplorerSort('holders')} style={{ cursor: 'pointer' }}>Holders {explorerSort.key === 'holders' ? (explorerSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th onClick={() => handleExplorerSort('total_interest')} style={{ cursor: 'pointer' }}>Total Interest {explorerSort.key === 'total_interest' ? (explorerSort.direction === 'asc' ? '🔼' : '🔽') : '↕️'}</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedExplorer.length > 0 ? sortedExplorer.map(s => {
                        const conditions = {
                            ema_50_above_200: s.condition_ema_50_200,
                            ema_200_slope_positive: s.condition_ema_200_slope,
                            at_6m_high: s.condition_6m_high,
                            volume_surge: s.condition_volume,
                            relative_strength: s.condition_rs,
                            breakout_10d: s.condition_breakout_10d,
                            price_quality: s.condition_price_quality
                        };
                        return (
                            <tr key={s.symbol} onClick={() => onSelectStock({ ...s, conditions, price: s.current_price })} className="clickable-row">
                                <td className="font-bold">
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        {s.is_breakout && <span title="🚀 BREAKOUT DETECTED" style={{ fontSize: '1.2rem' }}>🚀</span>}
                                        {s.symbol}
                                    </div>
                                </td>
                                <td>{s.is_breakout ? 'YES' : 'NO'}</td>
                                <td>{s.score !== null ? <span className="score-badge">{s.score}</span> : '-'}</td>
                                <td style={{ color: (s.rs_90d === 0 || s.rs_90d === null) ? '#ff4d4f' : 'inherit' }}>
                                    {s.rs_90d !== null ? s.rs_90d.toFixed(1) : '-'}
                                    {(s.rs_90d === 0 || s.rs_90d === null) && <span title="SUSPICIOUS RS: Calculation may have failed" style={{ marginLeft: '4px', cursor: 'help' }}>⚠️</span>}
                                </td>
                                <td>₹{s.current_price?.toLocaleString() || '-'}</td>
                                <td>{s.watchers}</td>
                                <td>{s.holders}</td>
                                <td style={{ fontWeight: 800 }}>{s.total_interest}</td>
                                <td>
                                    <button 
                                        onClick={(e) => handleRepairSymbol(e, s.symbol)}
                                        className="action-badge badge-skipped"
                                        style={{ background: '#ff4d4f', color: 'white', border: 'none', cursor: 'pointer', padding: '2px 8px', borderRadius: '4px' }}
                                        title="Surgical Repair: Reset all data and re-ingest"
                                    >
                                        🔄 Reset
                                    </button>
                                </td>
                            </tr>
                        );
                    }) : (
                        <tr>
                            <td colSpan={5} className="empty-state">No symbols matching "{searchTerm}" found.</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>

        <div style={{ marginTop: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', opacity: 0.8 }}>Add Global Symbol:</span>
            <input 
                type="text" 
                placeholder="RELIANCE.NS" 
                value={newSymbol}
                onChange={e => setNewSymbol(e.target.value.toUpperCase())}
                className="form-input"
                style={{ width: '150px', margin: 0, padding: '4px 8px' }}
            />
            <button onClick={handleAddGlobalSymbol} className="action-btn btn-executed" style={{ padding: '4px 12px' }}>Add</button>
        </div>
      </section>

      <div className="admin-grids" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '24px' }}>
        <section className="section">
           <h3 className="section-title">🔥 Trending (Watchlists)</h3>
           <div className="table-container">
             <table className="data-table">
                <thead><tr><th>Symbol</th><th>Watchers</th></tr></thead>
                <tbody>
                  {topStocks?.top_watched.map(s => (
                      <tr key={s.symbol}>
                          <td className="font-bold">{s.symbol}</td>
                          <td>{s.count} users</td>
                      </tr>
                  ))}
                  {(!topStocks?.top_watched.length) && (
                      <tr className="empty-state text-sm"><td colSpan={2}>No trending stocks found.</td></tr>
                  )}
                </tbody>
             </table>
           </div>
        </section>

        <section className="section">
           <h3 className="section-title">💰 Core holdings (Portfolios)</h3>
           <div className="table-container">
             <table className="data-table">
                <thead><tr><th>Symbol</th><th>Investors</th></tr></thead>
                <tbody>
                    {topStocks?.top_held.map(s => (
                        <tr key={s.symbol}>
                            <td className="font-bold">{s.symbol}</td>
                            <td>{s.count} users</td>
                        </tr>
                    ))}
                    {(!topStocks?.top_held.length) && (
                        <tr className="empty-state text-sm"><td colSpan={2}>No core holdings found.</td></tr>
                    )}
                </tbody>
             </table>
           </div>
        </section>
      </div>

      <section className="section" style={{ marginTop: '32px', borderTop: '1px solid #333', paddingTop: '24px' }}>
        <h3 className="section-title">⚖️ System Audit Trail (Compliance & Health)</h3>
        <p className="section-subtitle">Chronological record of all engine triggers, data validation events, and risk checks.</p>
        <div className="table-container" style={{ marginTop: '16px', maxHeight: '400px', overflowY: 'auto' }}>
            <table className="data-table audit-table">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Event</th>
                        <th>Severity</th>
                        <th>Message</th>
                        <th>Metadata</th>
                    </tr>
                </thead>
                <tbody>
                    {auditLogs.map(log => (
                        <tr key={log.id} style={{ background: log.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.05)' : 'transparent' }}>
                            <td className="text-xs opacity-70 mono">{new Date(log.timestamp).toLocaleString()}</td>
                            <td><span className="action-badge badge-executed">{log.event_type}</span></td>
                            <td>
                                <span className={`severity-tag ${log.severity.toLowerCase()}`} style={{ 
                                    padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 'bold',
                                    background: log.severity === 'CRITICAL' ? '#ef4444' : log.severity === 'WARNING' ? '#f59e0b' : '#22c55e',
                                    color: 'white'
                                }}>
                                    {log.severity}
                                </span>
                            </td>
                            <td style={{ fontSize: '0.85rem', maxWidth: '300px' }}>{log.message}</td>
                            <td className="text-xs opacity-50">
                                <pre style={{ margin: 0, fontSize: '0.65rem' }}>{JSON.stringify(log.metadata, null, 2)}</pre>
                            </td>
                        </tr>
                    ))}
                    {(!auditLogs.length) && (
                        <tr><td colSpan={5} className="empty-state">No audit logs found.</td></tr>
                    )}
                </tbody>
            </table>
        </div>
      </section>

      <style>{`
        .mono { font-family: monospace; }
        .empty-state { text-align: center; padding: 40px; color: #666; font-style: italic; }
        .clickable-row:hover { background: rgba(255,255,255,0.02); cursor: pointer; }
      `}</style>
    </div>
  );
}
