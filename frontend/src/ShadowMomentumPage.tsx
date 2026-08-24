import { useState, useEffect } from 'react';
import { api } from './api';
import BreakoutBadge from './BreakoutBadge';

export default /* ─── Shadow Momentum Page ────────────────────────────────── */
function ShadowMomentumPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    api.getShadowSignals()
      .then((res: any) => {
        setData(res);
        if (res?.error) {
          setLoadError(typeof res.error === 'string' ? res.error : 'Swing Momentum feed returned an unexpected response.');
        } else {
          setLoadError('');
        }
      })
      .catch((err: any) => {
        console.error(err);
        setLoadError(err?.message || 'Could not load the Swing Momentum feed.');
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Detecting market momentum...</div>;

  const stocks = data?.stocks || [];

  return (
    <div className="shadow-momentum">
      <h2 className="section-title">🔄 Swing Momentum (Shadow Picks)</h2>
      <p className="section-subtitle">
        The Top 10 highest-scoring stocks today. These ignore the Market Regime filter to help you identify
        active momentum even in Bear markets.
      </p>

      <div className="card" style={{ backgroundColor: '#1e3a8a30', borderColor: '#3b82f640', marginBottom: '24px' }}>
        <h4 style={{ margin: '0 0 8px 0', color: '#60a5fa' }}>💡 Trading Rule</h4>
        <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8', lineHeight: 1.4 }}>
          In a <strong>BEAR</strong> market, only consider entering stocks tagged with <strong>🚀 BREAKOUT</strong>.
          This ensures the stock is actively clearing a ceiling with high volume before you jump in.
        </p>
      </div>

      {loadError && (
        <div className="empty-state" style={{ marginBottom: '20px' }}>
          ⚠️ Swing Momentum could not load cleanly: {loadError}
        </div>
      )}

      {!loadError && stocks.length === 0 && (
        <div className="empty-state" style={{ marginBottom: '20px' }}>
          No swing momentum candidates are available right now. This usually means today&apos;s shadow feed is empty or the latest score snapshot has not populated yet.
        </div>
      )}

      <div className="signals-grid">
        {stocks.map((s: any) => {
          const conditions = {
            ema_50_above_200: s.condition_ema_50_200,
            ema_200_slope_positive: s.condition_ema_200_slope,
            at_6m_high: s.condition_6m_high,
            volume_surge: s.condition_volume,
            relative_strength: s.condition_rs,
            breakout_10d: s.condition_breakout_10d,
            price_quality: s.condition_price_quality
          };
          const isGoldenSetup = s.total_score === 100;
          const isBreakout = !!s.condition_breakout_10d;
          const stockWithConditions = { ...s, score: s.total_score, price: s.close, conditions };

          return (
            <div
              key={s.symbol}
              className={`signal-card ${isBreakout ? 'signal-buy' : ''} clickable-row`}
              style={{ borderLeftWidth: isBreakout ? '4px' : '1px', borderLeftColor: isBreakout ? '#22c55e' : '#334155' }}
              onClick={() => onSelectStock(stockWithConditions)}
            >
              <div className="signal-header">
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className="signal-symbol">{s.symbol}</span>
                    <BreakoutBadge state={s.breakout_state} ageInfo={s.age_info} />
                  </div>
                  {isGoldenSetup && <span className="score-trend-indicator" style={{ fontSize: '10px', marginTop: '2px', color: '#22c55e', fontWeight: 800 }}>🚀 GOLDEN SETUP</span>}
                  {isBreakout && !isGoldenSetup && <span className="score-trend-indicator" style={{ fontSize: '10px', marginTop: '2px', color: '#60a5fa', fontWeight: 800 }}>✨ BREAKOUT</span>}
                </div>
                <span className="score-badge" style={{ fontSize: '14px', padding: '4px 10px' }}>{s.total_score}</span>
              </div>
              <div className="signal-details">
                <div className="signal-detail"><span className="detail-label">Price</span><span className="detail-value">₹{s.close?.toLocaleString()}</span></div>
                <div className="signal-detail">
                  <span className="detail-label">V-Surge</span>
                  <span className="detail-value" style={{ color: s.condition_volume ? '#22c55e' : '#94a3b8' }}>
                    {s.condition_volume ? 'YES' : 'No'}
                  </span>
                </div>
              </div>
              <div style={{ marginTop: '8px', display: 'flex', gap: '4px' }}>
                <span style={{ fontSize: '10px', color: s.condition_ema_50_200 ? '#22c55e' : '#475569' }}>EMA {s.condition_ema_50_200 ? '✅' : '○'}</span>
                <span style={{ fontSize: '10px', color: s.condition_ema_200_slope ? '#22c55e' : '#475569' }}>Slope {s.condition_ema_200_slope ? '✅' : '○'}</span>
                <span style={{ fontSize: '10px', color: s.condition_rs ? '#22c55e' : '#475569' }}>RS {s.condition_rs ? '✅' : '○'}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
