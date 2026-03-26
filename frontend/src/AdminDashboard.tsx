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

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [topStocks, setTopStocks] = useState<{ top_watched: any[], top_held: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const loadAdminIntel = async () => {
    try {
      setLoading(true);
      const [m, c] = await Promise.all([
        api.getAdminMetrics(),
        api.getAdminTopStocks()
      ]);
      setMetrics(m);
      setTopStocks(c);
    } catch (err: any) {
      setError(err.message || 'Failed to load intel');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminIntel();
  }, []);

  // Combined unique symbols for the "Global Explorer"
  const allSymbols = Array.from(new Set([
    ...(topStocks?.top_watched?.map(s => s.symbol) || []),
    ...(topStocks?.top_held?.map(s => s.symbol) || [])
  ])).filter(s => s.toLowerCase().includes(searchTerm.toLowerCase()));

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
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {allSymbols.length > 0 ? allSymbols.map(sym => {
                        const isWatched = topStocks?.top_watched.some(s => s.symbol === sym);
                        const isHeld = topStocks?.top_held.some(s => s.symbol === sym);
                        return (
                            <tr key={sym}>
                                <td className="font-bold">{sym}</td>
                                <td>
                                    {isHeld && <span className="action-badge badge-executed" style={{ marginRight: '4px' }}>HELD</span>}
                                    {isWatched && <span className="action-badge badge-skipped">WATCHED</span>}
                                </td>
                                <td>
                                    <button className="link-btn" onClick={() => (window as any).location.search = `?q=${sym}`}>Analytics (Soon)</button>
                                </td>
                            </tr>
                        );
                    }) : (
                        <tr>
                            <td colSpan={3} className="empty-state">No symbols matching "{searchTerm}" found.</td>
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
