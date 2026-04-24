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
  total_symbols: int;
  null_indicators: int;
  suspicious_rs: int;
  stale_indicators: int;
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
  const [loading, setLoading] = useState(true);
  const [isRecovering, setIsRecovering] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Sorting states
  const [leaderboardSort, setLeaderboardSort] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'total_score', direction: 'desc' });
  const [explorerSort, setGlobalSort] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'total_interest', direction: 'desc' });

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
    const fetchHealth = async () => {
      try { const data = await api.getAdminDataHealth(); setHealth(data); }
      catch (e) { console.error('Health metrics failed', e); }
    };

    await Promise.allSettled([fetchMetrics(), fetchTop(), fetchGlobal(), fetchLeaderboard(), fetchHallOfFame(), fetchShadow(), fetchHealth()]);
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
                style={{ width: '100%', height: '100%', fontSize: '0.9rem' }}
            >
                {isRecovering ? '⏳ Repairing...' : '🛠️ Force Repair'}
            </button>
        </div>
      </div>

      {error && <div className="error-alert">{error}</div>}

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
                            relative_strength: s.condition_rs
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
        <h3 className="section-title">🕵️ Strategy Shadow Tracker</h3>
        <p className="section-subtitle">What the Top 10 looks like today (ignores Market Regime filters).</p>
        <div className="table-container" style={{ marginTop: '16px' }}>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>First Entered Top 10</th>
                        <th>Status</th>
                        <th>Entry Price</th>
                        <th>Current Price</th>
                        <th>Total Return %</th>
                    </tr>
                </thead>
                <tbody>
                    {strategyShadow.map(s => (
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
        <h3 className="section-title">🏛️ Hall of Fame (High Score Performance)</h3>
        <p className="section-subtitle">Tracking stocks from their first 75+ score appearance in MRI.</p>
        <div className="table-container" style={{ marginTop: '16px' }}>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>First Seen</th>
                        <th>Entry Price</th>
                        <th>Current Price</th>
                        <th>Perf %</th>
                        <th>Max Score</th>
                    </tr>
                </thead>
                <tbody>
                    {hallOfFame.map(s => (
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
                            relative_strength: s.condition_rs
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
    </div>
  );
}
