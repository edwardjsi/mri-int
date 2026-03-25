// @ts-nocheck
// v2-build-fix
import { useState, useEffect } from 'react';
import { api } from './api';

interface AdminMetrics {
  total_users: number;
  active_watchlists: number;
  active_portfolios: number;
}

interface TopStock {
  symbol: string;
  count: number;
  total_shares?: number;
}

interface AdminData {
  top_watched: TopStock[];
  top_held: TopStock[];
}

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [data, setData] = useState<AdminData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadAdminData = async () => {
    try {
      setLoading(true);
      const [m, d] = await Promise.all([
        api.getAdminMetrics(),
        api.getAdminTopStocks()
      ]);
      setMetrics(m);
      setData(d);
    } catch (err: any) {
      setError(err.message || 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  if (loading) return <div className="loading">Loading Admin Intel...</div>;
  if (error) return <div className="error-alert">{error}</div>;

  return (
    <div className="admin-dashboard">
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Total Platform Users</div>
          <div className="stat-value">{metrics?.total_users}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Watchlists</div>
          <div className="stat-value">{metrics?.active_watchlists}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Digital Twins</div>
          <div className="stat-value">{metrics?.active_portfolios}</div>
        </div>
        <div className={`stat-card ${metrics?.last_ingestion && (new Date().getTime() - new Date(metrics.last_ingestion).getTime() > 86400000) ? 'status-critical' : ''}`}>
          <div className="stat-label">Last Market Data</div>
          <div className="stat-value" style={{ fontSize: '1.2rem' }}>
            {metrics?.last_ingestion ? new Date(metrics.last_ingestion).toLocaleDateString() : 'Never'}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '4px' }}>
            {metrics?.last_ingestion && (new Date().getTime() - new Date(metrics.last_ingestion).getTime() > 86400000) ? '⚠️ Outdated' : '✅ Up to date'}
          </div>
        </div>
      </div>

      <div className="admin-grids" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '24px' }}>
        <section className="section">
          <h3 className="section-title">🔥 Most Watched Stocks</h3>
          <p className="section-subtitle">Aggregated interest across all user watchlists.</p>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Symbol</th>
                  <th>Watchers</th>
                </tr>
              </thead>
              <tbody>
                {data?.top_watched && data.top_watched.length > 0 ? (
                  data.top_watched.map((s, i) => (
                    <tr key={s.symbol}>
                      <td>#{i + 1}</td>
                      <td className="font-bold">{s.symbol}</td>
                      <td>{s.count} users</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} className="empty-state" style={{ padding: '2rem' }}>
                      There are no stocks in user watchlists to track here right now. When users add, they will be displayed.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="section">
          <h3 className="section-title">💰 Most Held Stocks</h3>
          <p className="section-subtitle">Aggregated holdings across all user portfolios.</p>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Symbol</th>
                  <th>Holders</th>
                  <th>Total Qty</th>
                </tr>
              </thead>
              <tbody>
                {data?.top_held && data.top_held.length > 0 ? (
                  data.top_held.map((s, i) => (
                    <tr key={s.symbol}>
                      <td>#{i + 1}</td>
                      <td className="font-bold">{s.symbol}</td>
                      <td>{s.count} users</td>
                      <td>{Number(s.total_shares).toLocaleString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="empty-state" style={{ padding: '2rem' }}>
                      There are no stocks in user portfolios to track here right now. When users add, they will be displayed.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
      
      <div style={{ marginTop: '24px', textAlign: 'center' }}>
         <button className="btn-secondary" onClick={loadAdminData}>🔄 Refresh Metrics</button>
      </div>
    </div>
  );
}
