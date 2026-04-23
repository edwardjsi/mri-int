// @ts-nocheck
import { useState, useEffect } from 'react';
import { api } from './api';

interface AdminMetrics {
  total_users: number;
  active_watchlists: number;
  active_portfolios: number;
  last_ingestion: string | null;
}

interface SymbolGrade {
  symbol: string;
  total_score: number | null;
  last_score_date: string | null;
  interest_count: number; // How many users track/hold this
}

export default function AdminDashboard({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [topStocks, setTopStocks] = useState<{ top_watched: any[], top_held: any[] } | null>(null);
  const [dailyLeaderboard, setDailyLeaderboard] = useState<{ date: string | null, top_stocks: any[] }>({ date: null, top_stocks: [] });
  const [globalUniverse, setGlobalUniverse] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

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

    await Promise.allSettled([fetchMetrics(), fetchTop(), fetchGlobal(), fetchLeaderboard()]);
    setLoading(false);
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
            <div className="stat-label">Market Freshness</div>
            <div className={`stat-value ${metrics?.last_ingestion && (new Date().getTime() - new Date(metrics.last_ingestion).getTime() > 86400000) ? 'status-critical' : ''}`} style={{ fontSize: '1.2rem' }}>
                {metrics?.last_ingestion ? new Date(metrics.last_ingestion).toLocaleDateString() : 'Pending'}
            </div>
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
                        <th>Symbol</th>
                        <th>Score</th>
                        <th>Price</th>
                        <th>Breakdown (EMA | Slope | RS | High | Vol)</th>
                    </tr>
                </thead>
                <tbody>
                    {dailyLeaderboard.top_stocks.map(s => {
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
                        <th>Symbol</th>
                        <th>Score</th>
                        <th>Watchers</th>
                        <th>Holders</th>
                        <th>Total Interest</th>
                    </tr>
                </thead>
                <tbody>
                    {filteredSymbols.length > 0 ? filteredSymbols.map(s => {
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
                                    {s.symbol}
                                    {s.is_breakout && <span className="score-trend-indicator" style={{ marginLeft: '8px' }}>🚀 BREAKOUT</span>}
                                    {s.score === null && <span className="action-badge badge-skipped" style={{ padding: '2px 4px', fontSize: '10px', marginLeft: '8px', background: '#faad14' }}>⏳ PENDING</span>}
                                </td>
                                <td>{s.score !== null ? <span className="score-badge">{s.score}</span> : '-'}</td>
                                <td>{s.watchers}</td>
                                <td>{s.holders}</td>
                                <td style={{ fontWeight: 800 }}>{s.total_interest}</td>
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
