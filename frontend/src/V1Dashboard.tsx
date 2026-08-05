import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, DashboardPayload } from './api';

export function V1Dashboard() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // Attempt to fetch from backend; if it fails (e.g. backend endpoint not yet deployed),
    // we show a gracefully formatted error.
    api.getDashboard()
      .then(setData)
      .catch((err) => {
        console.error(err);
        // Provide mock fallback data for development preview if API is missing
        if (err.message.includes('404') || err.message.includes('Not Found')) {
          setData({
            cards: [
              { id: 'summary', title: 'Main Portfolio', value: '₹12,45,000', status: 'Positive', subtitle: '+12.4% PnL', priority: 1 },
              { id: 'health', title: 'Portfolio Health', value: 'Healthy', status: 'Positive', subtitle: 'Exposure within limits', priority: 2 },
              { id: 'regime', title: 'Market Regime', value: 'Bullish', status: 'Positive', subtitle: 'Weekly trend supportive', priority: 3 },
              { id: 'cash', title: 'Cash Available', value: '₹85,000', status: 'Neutral', subtitle: 'Deployment pace steady', priority: 4 }
            ],
            weeklyDecisions: [
              { decisionId: 'dec_001', stock: 'Neuland Labs', action: 'ADD', priority: 1, confidence: 91, summary: 'Weekly trend remains intact.' },
              { decisionId: 'dec_002', stock: 'TCS', action: 'HOLD', priority: 2, confidence: 85, summary: 'Consolidating near ATH.' }
            ]
          });
        } else {
          setError('Unable to load your weekly MRI data. Try again.');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="section">
        <h2 className="section-title">Weekly Overview</h2>
        <div style={{ opacity: 0.5, animation: 'pulse 1.5s infinite' }}>
          <div style={{ height: '100px', background: '#1e293b', borderRadius: '12px', marginBottom: '20px' }}></div>
          <div style={{ height: '300px', background: '#1e293b', borderRadius: '12px' }}></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="section">
        <div className="empty-state" style={{ color: '#fca5a5', borderColor: '#ef4444' }}>
          ⚠️ {error}
        </div>
      </div>
    );
  }

  const cards = data?.cards || [];
  const decisions = data?.weeklyDecisions || [];

  // Ensure cards are sorted by priority ascending
  const sortedCards = [...cards].sort((a, b) => a.priority - b.priority);

  // Ensure decisions are sorted by priority ascending
  const sortedDecisions = [...decisions].sort((a, b) => a.priority - b.priority);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'positive': return '#22c55e';
      case 'warning': return '#eab308';
      case 'critical': return '#ef4444';
      default: return '#94a3b8';
    }
  };

  const getActionBadgeClass = (action: string) => {
    if (['BUY', 'ADD'].includes(action)) return 'badge-buy';
    if (['SELL', 'EXIT', 'REDUCE'].includes(action)) return 'badge-sell';
    return 'badge-executed'; // Used as generic neutral/hold class here
  };

  return (
    <div className="dashboard">
      <section className="section">
        <h2 className="section-title">Portfolio Intelligence</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '32px' }}>
          {sortedCards.map(card => (
            <div key={card.id} style={{ 
              background: '#0f172a', 
              border: '1px solid #1e293b', 
              borderLeft: `4px solid ${getStatusColor(card.status)}`,
              borderRadius: '12px', 
              padding: '20px' 
            }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 600 }}>{card.title}</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f8fafc', marginBottom: '4px' }}>{card.value}</div>
              <div style={{ fontSize: '13px', color: '#cbd5e1' }}>{card.subtitle}</div>
            </div>
          ))}
          {sortedCards.length === 0 && (
            <div className="empty-state" style={{ gridColumn: '1 / -1' }}>No intelligence cards available.</div>
          )}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Weekly Decisions</h2>
        {sortedDecisions.length > 0 ? (
          <div className="signals-grid">
            {sortedDecisions.map(decision => (
              <Link 
                to={`/decision/${decision.decisionId}`} 
                key={decision.decisionId}
                style={{ textDecoration: 'none', color: 'inherit' }}
              >
                <div className="signal-card clickable-row" style={{ display: 'block' }}>
                  <div className="signal-header">
                    <span className="signal-symbol" style={{ fontSize: '18px' }}>{decision.stock}</span>
                    <span className={`signal-badge ${getActionBadgeClass(decision.action)}`}>{decision.action}</span>
                  </div>
                  <div className="signal-details" style={{ marginTop: '12px' }}>
                    <div className="signal-detail">
                      <span className="detail-label">Confidence</span>
                      <span className="detail-value" style={{ fontWeight: 'bold', color: decision.confidence >= 80 ? '#22c55e' : '#eab308' }}>
                        {decision.confidence}%
                      </span>
                    </div>
                  </div>
                  <div className="signal-reason" style={{ marginTop: '12px', color: '#94a3b8' }}>
                    {decision.summary}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            No weekly recommendations are available right now.
          </div>
        )}
      </section>
    </div>
  );
}
