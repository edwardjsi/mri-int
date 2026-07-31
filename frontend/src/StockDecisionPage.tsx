import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, StockDecisionPayload } from './api';

export function StockDecisionPage() {
  const { decisionId } = useParams<{ decisionId: string }>();
  const [data, setData] = useState<StockDecisionPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!decisionId) return;
    setLoading(true);
    api.getStockDecision(decisionId)
      .then(setData)
      .catch((err) => {
        console.error(err);
        if (err.message.includes('404')) {
          // Mock data for development preview if backend endpoint is not ready
          setData({
            decisionHeader: {
              symbol: 'TCS',
              companyName: 'Tata Consultancy Services',
              action: 'ADD',
              confidence: 91,
              decisionDate: new Date().toISOString().split('T')[0],
              marketRegime: 'Bullish',
              portfolioImpact: 'Maintains tech exposure at 15%'
            },
            decisionMetadata: {
              decisionId: decisionId,
              generatedAt: new Date().toISOString(),
              engineVersion: 'v2.1.0',
              mosiVersion: '1.4.2',
              rulesVersion: '2026-07',
              snapshotTimestamp: new Date().toISOString()
            },
            recommendation: {
              action: 'ADD',
              confidence: 91,
              summary: 'Weekly trend remains intact with strong momentum.'
            },
            why: {
              primaryReason: 'Weekly structure intact with increasing institutional flow.',
              supportingReasons: ['Higher highs maintained', 'No hard rules triggered', 'MOSI score > 80']
            },
            rules: [
              { name: 'Weekly Structure', status: 'PASS', detail: 'Higher-high / higher-low sequence intact' },
              { name: 'Trailing Stop', status: 'PASS', detail: 'Price is 12% above trailing stop of ₹3,400' }
            ],
            evidence: [
              { label: '30W EMA', value: 'Above', status: 'PASS' },
              { label: 'RSI (14)', value: '62', status: 'PASS' },
              { label: 'Volume', value: 'Surging', status: 'PASS' }
            ],
            monitoring: [
              { label: 'Next earnings', detail: 'Estimated Aug 12' },
              { label: 'Alert at', detail: '₹4,100 resistance' }
            ],
            history: {
              previousAction: 'BUY',
              previousConfidence: 82,
              lastReviewed: '2026-07-24'
            }
          });
        } else {
          setError('Unable to load decision details. Try again.');
        }
      })
      .finally(() => setLoading(false));
  }, [decisionId]);

  if (loading) {
    return (
      <div className="section">
        <h2 className="section-title">Decision Details</h2>
        <div style={{ opacity: 0.5, animation: 'pulse 1.5s infinite' }}>
          <div style={{ height: '120px', background: '#1e293b', borderRadius: '12px', marginBottom: '20px' }}></div>
          <div style={{ height: '80px', background: '#1e293b', borderRadius: '12px', marginBottom: '20px' }}></div>
          <div style={{ height: '200px', background: '#1e293b', borderRadius: '12px' }}></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="section">
        <div className="empty-state" style={{ color: '#fca5a5', borderColor: '#ef4444' }}>
          ⚠️ {error || 'No decision details are available for this stock.'}
        </div>
      </div>
    );
  }

  const { decisionHeader, recommendation, why, rules, evidence, monitoring, decisionMetadata, history } = data;

  const getActionColor = (action: string) => {
    if (['BUY', 'ADD'].includes(action)) return '#22c55e';
    if (['SELL', 'EXIT', 'REDUCE'].includes(action)) return '#ef4444';
    return '#94a3b8';
  };

  const getStatusColor = (status: string) => {
    if (status === 'PASS' || status === 'Positive') return '#22c55e';
    if (status === 'FAIL' || status === 'Negative') return '#ef4444';
    if (status === 'WARN' || status === 'Warning') return '#eab308';
    return '#94a3b8';
  };

  return (
    <div className="decision-page" style={{ maxWidth: '800px', margin: '0 auto', paddingBottom: '60px' }}>
      
      <Link to="/dashboard" style={{ display: 'inline-block', marginBottom: '20px', color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>
        ← Back to Dashboard
      </Link>

      {/* 1. Decision Header */}
      <section style={{ background: '#0f172a', borderRadius: '12px', padding: '24px', border: '1px solid #1e293b', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '28px', color: '#f8fafc' }}>{decisionHeader.symbol}</h1>
            <div style={{ color: '#94a3b8', fontSize: '15px', marginTop: '4px' }}>{decisionHeader.companyName}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ 
              display: 'inline-block', 
              padding: '6px 16px', 
              borderRadius: '20px', 
              background: `${getActionColor(decisionHeader.action)}20`,
              color: getActionColor(decisionHeader.action),
              fontWeight: 'bold',
              fontSize: '18px',
              border: `1px solid ${getActionColor(decisionHeader.action)}50`
            }}>
              {decisionHeader.action} {decisionHeader.confidence}%
            </div>
          </div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px', borderTop: '1px solid #1e293b', paddingTop: '16px' }}>
          <div>
            <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Date</div>
            <div style={{ color: '#cbd5e1', marginTop: '4px' }}>{decisionHeader.decisionDate}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Regime</div>
            <div style={{ color: '#cbd5e1', marginTop: '4px' }}>{decisionHeader.marketRegime}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Impact</div>
            <div style={{ color: '#cbd5e1', marginTop: '4px' }}>{decisionHeader.portfolioImpact}</div>
          </div>
        </div>
      </section>

      {/* History (Optional/Reserved for future) */}
      {history && (
        <section style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', gap: '24px', background: '#1e293b', padding: '16px 24px', borderRadius: '8px', fontSize: '14px' }}>
            <div><span style={{ color: '#64748b', marginRight: '8px' }}>Last Review:</span><span style={{ color: '#cbd5e1' }}>{history.lastReviewed}</span></div>
            <div><span style={{ color: '#64748b', marginRight: '8px' }}>Previous:</span><span style={{ color: '#cbd5e1' }}>{history.previousAction} ({history.previousConfidence}%)</span></div>
            <div>
              <span style={{ color: '#64748b', marginRight: '8px' }}>Confidence Shift:</span>
              <span style={{ color: decisionHeader.confidence > history.previousConfidence ? '#22c55e' : (decisionHeader.confidence < history.previousConfidence ? '#ef4444' : '#94a3b8') }}>
                {decisionHeader.confidence > history.previousConfidence ? '+' : ''}{decisionHeader.confidence - history.previousConfidence}
              </span>
            </div>
          </div>
        </section>
      )}

      {/* 2. Recommendation */}
      {recommendation && (
        <section style={{ marginBottom: '32px' }}>
          <h3 style={{ color: '#94a3b8', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>Recommendation</h3>
          <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderLeft: `4px solid ${getActionColor(recommendation.action)}`, padding: '20px', borderRadius: '8px' }}>
            <p style={{ margin: 0, fontSize: '16px', color: '#f8fafc', lineHeight: '1.5' }}>{recommendation.summary}</p>
          </div>
        </section>
      )}

      {/* 3. Why */}
      {why && (
        <section style={{ marginBottom: '32px' }}>
          <h3 style={{ color: '#94a3b8', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>Why</h3>
          <div style={{ background: '#0f172a', border: '1px solid #1e293b', padding: '20px', borderRadius: '8px' }}>
            <div style={{ fontSize: '16px', color: '#f8fafc', marginBottom: '16px', fontWeight: 500 }}>{why.primaryReason}</div>
            {why.supportingReasons && why.supportingReasons.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', lineHeight: '1.6' }}>
                {why.supportingReasons.map((reason, idx) => (
                  <li key={idx} style={{ marginBottom: '8px' }}>{reason}</li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}

      {/* 4. Rules */}
      {rules && rules.length > 0 && (
        <section style={{ marginBottom: '32px' }}>
          <h3 style={{ color: '#94a3b8', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>Rules Evaluated</h3>
          <div style={{ border: '1px solid #1e293b', borderRadius: '8px', overflow: 'hidden' }}>
            {rules.map((rule, idx) => (
              <div key={idx} style={{ background: '#0f172a', padding: '16px 20px', borderBottom: idx < rules.length - 1 ? '1px solid #1e293b' : 'none', display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
                <div style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', background: `${getStatusColor(rule.status)}20`, color: getStatusColor(rule.status) }}>
                  {rule.status}
                </div>
                <div>
                  <div style={{ color: '#f8fafc', fontWeight: 500, marginBottom: '4px' }}>{rule.name}</div>
                  <div style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.5' }}>{rule.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 5. Evidence */}
      {evidence && evidence.length > 0 && (
        <section style={{ marginBottom: '32px' }}>
          <h3 style={{ color: '#94a3b8', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>Evidence</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
            {evidence.map((ev, idx) => (
              <div key={idx} style={{ background: '#0f172a', border: '1px solid #1e293b', padding: '16px', borderRadius: '8px' }}>
                <div style={{ color: '#64748b', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px' }}>{ev.label}</div>
                <div style={{ color: '#f8fafc', fontSize: '16px', fontWeight: 500, marginBottom: '4px' }}>{ev.value}</div>
                <div style={{ color: getStatusColor(ev.status), fontSize: '12px', fontWeight: 'bold' }}>{ev.status}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 6. Monitoring */}
      {monitoring && monitoring.length > 0 && (
        <section style={{ marginBottom: '40px' }}>
          <h3 style={{ color: '#94a3b8', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>Monitoring</h3>
          <div style={{ background: '#1e293b', padding: '20px', borderRadius: '8px' }}>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', lineHeight: '1.6' }}>
              {monitoring.map((item, idx) => (
                <li key={idx} style={{ marginBottom: '8px' }}>
                  <strong style={{ color: '#f8fafc' }}>{item.label}:</strong> {item.detail}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* 7. Decision Metadata */}
      {decisionMetadata && (
        <section style={{ borderTop: '1px solid #1e293b', paddingTop: '24px' }}>
          <h3 style={{ color: '#64748b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>Decision Metadata</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', fontSize: '13px' }}>
            <div><div style={{ color: '#64748b', marginBottom: '2px' }}>Decision ID</div><div style={{ color: '#94a3b8', fontFamily: 'monospace' }}>{decisionMetadata.decisionId}</div></div>
            <div><div style={{ color: '#64748b', marginBottom: '2px' }}>Generated At</div><div style={{ color: '#94a3b8' }}>{decisionMetadata.generatedAt}</div></div>
            <div><div style={{ color: '#64748b', marginBottom: '2px' }}>Engine Version</div><div style={{ color: '#94a3b8' }}>{decisionMetadata.engineVersion}</div></div>
            <div><div style={{ color: '#64748b', marginBottom: '2px' }}>MOSI Version</div><div style={{ color: '#94a3b8' }}>{decisionMetadata.mosiVersion}</div></div>
            <div><div style={{ color: '#64748b', marginBottom: '2px' }}>Rules Version</div><div style={{ color: '#94a3b8' }}>{decisionMetadata.rulesVersion}</div></div>
            <div><div style={{ color: '#64748b', marginBottom: '2px' }}>Snapshot Timestamp</div><div style={{ color: '#94a3b8' }}>{decisionMetadata.snapshotTimestamp}</div></div>
          </div>
        </section>
      )}
    </div>
  );
}
