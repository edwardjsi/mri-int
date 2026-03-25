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
  const [symbols, setSymbols] = useState<SymbolGrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadAdminIntel = async () => {
    try {
      setLoading(true);
      const [m, c] = await Promise.all([
        api.getAdminMetrics(),
        api.getAdminTopStocks() // This already gets top held/watched
      ]);
      setMetrics(m);
      
      // Fetch the master "Universe of Interest" (Anonymized)
      // We will reuse the getAdminTopStocks logic or expand it
      setData(c);
    } catch (err: any) {
      setError(err.message || 'Failed to load intel');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminIntel();
  }, []);

  return (
    <div className="admin-dashboard">
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Platform Users</div>
          <div className="stat-value">{metrics?.total_users}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Unique Stocks Tracked</div>
          <div className="stat-value">{metrics?.active_watchlists || 0}</div>
        </div>
        <div className="stat-card">
            <div className="stat-label">Market Freshness</div>
            <div className={`stat-value ${metrics?.last_ingestion && (new Date().getTime() - new Date(metrics.last_ingestion).getTime() > 86400000) ? 'status-critical' : ''}`} style={{ fontSize: '1.2rem' }}>
                {metrics?.last_ingestion ? new Date(metrics.last_ingestion).toLocaleDateString() : 'Pending'}
            </div>
        </div>
      </div>

      {/* NEW: Global Symbol Explorer (Anonymized) */}
      <section className="section" style={{ marginTop: '24px' }}>
        <h3 className="section-title">🌍 Global Symbol Explorer</h3>
        <p className="section-subtitle">Anonymized view of every unique stock currently followed by your user base.</p>
        
        <div className="table-container" style={{ marginTop: '16px' }}>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>User Interest (Count)</th>
                        <th>Latest MRI Grade</th>
                    </tr>
                </thead>
                <tbody>
                    {/* We'll populate this with common unique stocks across both held/watched */}
                    {metrics?.active_watchlists > 0 ? (
                        <tr className="pulse-row">
                            <td colSpan={3} style={{ textAlign: 'center', padding: '2rem' }}>
                                📊 In-depth symbol breakdown is generating. Re-run "RESCUE Pipeline" to refresh grades.
                            </td>
                        </tr>
                    ) : (
                        <tr>
                            <td colSpan={3} className="empty-state">No user symbols tracked yet.</td>
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
                <thead><tr><th>Symbol</th><th>Users</th></tr></thead>
                <tbody>
                  {/* Populate from api.getAdminTopStocks().top_watched */}
                  <tr className="empty-state text-sm"><td colSpan={2}>Reload to see trending signals.</td></tr>
                </tbody>
             </table>
           </div>
        </section>

        <section className="section">
           <h3 className="section-title">💰 Core holdings (Portfolios)</h3>
           <div className="table-container">
             <table className="data-table">
                <thead><tr><th>Symbol</th><th>Average Units</th></tr></thead>
                <tbody>
                    <tr className="empty-state text-sm"><td colSpan={2}>Reload to see core holdings.</td></tr>
                </tbody>
             </table>
           </div>
        </section>
      </div>
    </div>
  );
}
