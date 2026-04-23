// @ts-nocheck
// v2-build-fix
import { useState, useEffect, useMemo } from 'react';
import { api, isAuthenticated, isAdmin, getClientName, clearAuth } from './api';
import AdminDashboard from './AdminDashboard';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import './App.css';

/* ─── Score Breakdown Component ─── */
function ScoreBreakdown({ conditions, score }: { conditions: any, score: number }) {
  if (!conditions) return <div className="empty-state">No breakdown available for this score.</div>;

  const items = [
    { label: 'Trend Integrity (EMA 50 > 200)', value: conditions.ema_50_above_200, weight: '25%' },
    { label: 'Long-term Bias (200 EMA Slope > 0)', value: conditions.ema_200_slope_positive, weight: '25%' },
    { label: 'Outperformance (90d RS > 0)', value: conditions.relative_strength, weight: '20%' },
    { label: 'Alpha-Strength (Near 6m High)', value: conditions.at_6m_high, weight: '20%' },
    { label: 'Liquidity Gate (Volume Surge)', value: conditions.volume_surge, weight: '10%' },
  ];

  return (
    <div className="score-breakdown">
      <div className="summary-stat" style={{ marginBottom: '1rem', textAlign: 'center' }}>
        <span className="summary-label">Total MRI Score</span>
        <div className="stat-value" style={{ fontSize: '2rem', color: '#60a5fa' }}>{score}/100</div>
      </div>
      {items.map((item, idx) => (
        <div key={idx} className="condition-item">
          <div className="condition-label">
            {item.label}
            <div style={{ fontSize: '10px', color: '#64748b' }}>Weight: {item.weight}</div>
          </div>
          <div className={`condition-value ${item.value ? 'condition-pass' : 'condition-fail'}`}>
            {item.value ? '✅ PASS' : '❌ FAIL'}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─── Stock Details Modal ────────────────────────────────── */
function StockDetailsModal({ stock, onClose }: { stock: any, onClose: () => void }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h3 className="modal-title" style={{ marginBottom: '4px' }}>{stock.symbol}</h3>
            <div className="card-meta">Detailed MRI Intelligence Report</div>
          </div>
          <button className="link-btn" onClick={onClose} style={{ fontSize: '24px' }}>&times;</button>
        </div>
        
        <div className="modal-info" style={{ marginTop: '1.5rem' }}>
          <div className="info-row">
            <span>Current Price:</span>
            <span className="font-bold">₹{stock.current_price?.toLocaleString() || stock.price?.toLocaleString() || 'N/A'}</span>
          </div>
          {stock.pnl_pct !== undefined && (
            <div className="info-row">
              <span>Your P&L:</span>
              <span className="font-bold" style={{ color: stock.pnl_pct >= 0 ? '#22c55e' : '#ef4444' }}>
                {stock.pnl_pct >= 0 ? '+' : ''}{stock.pnl_pct}%
              </span>
            </div>
          )}
        </div>

        <ScoreBreakdown 
          score={stock.score || stock.total_score} 
          conditions={stock.conditions} 
        />

        <div className="modal-actions" style={{ marginTop: '1.5rem' }}>
          <button className="btn-primary" onClick={onClose}>Close Report</button>
        </div>
      </div>
    </div>
  );
}

/* ─── Login Page ─────────────────────────────────────────── */
function LoginPage({ onLogin, onCancel }: { onLogin: () => void; onCancel?: () => void }) {
  const [isRegister, setIsRegister] = useState(false);
  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [capital, setCapital] = useState('100000');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);

    const sanitizedEmail = email.trim();
    const sanitizedPassword = password.trim();

    try {
      if (isForgotPassword) {
        const res = await api.forgotPassword(sanitizedEmail);
        setSuccessMsg(res.message || 'Password reset link sent! Check your email.');
      } else if (isRegister) {
        await api.register(sanitizedEmail, name.trim(), sanitizedPassword, parseFloat(capital));
        onLogin();
      } else {
        await api.login(sanitizedEmail, sanitizedPassword);
        onLogin();
      }
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1 className="brand-title">📊 MRI</h1>
          <p className="brand-subtitle">Market Regime Intelligence</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          <h2 className="form-title">
            {isForgotPassword ? 'Reset Password' : (isRegister ? 'Create Account' : 'Sign In')}
          </h2>

          {error && <div className="error-alert">{error}</div>}
          {successMsg && <div className="success-alert" style={{ color: '#15803d', backgroundColor: '#dcfce7', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>{successMsg}</div>}

          {isRegister && !isForgotPassword && (
            <input type="text" placeholder="Full Name" value={name} onChange={e => setName(e.target.value)} className="form-input" required />
          )}

          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} className="form-input" required />

          {!isForgotPassword && (
            <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} className="form-input" required minLength={6} />
          )}

          {isRegister && !isForgotPassword && (
            <input type="number" placeholder="Initial Capital (₹)" value={capital} onChange={e => setCapital(e.target.value)} className="form-input" min="10000" />
          )}

          <button 
            type="submit" 
            className="btn-primary" 
            disabled={loading}
          >
            {loading ? 'Please wait...' : (isForgotPassword ? 'Send Reset Link' : (isRegister ? 'Create Account' : 'Sign In'))}
          </button>
          <div className="toggle-text" style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
            {!isForgotPassword && (
              <button type="button" className="link-btn" style={{ alignSelf: 'center' }} onClick={() => { setIsForgotPassword(true); setError(''); setSuccessMsg(''); }}>
                Forgot your password?
              </button>
            )}

            <p style={{ textAlign: 'center' }}>
              {isForgotPassword ? 'Remember your password?' : (isRegister ? 'Already have an account?' : "Don't have an account?")}{' '}
              <button type="button" className="link-btn" onClick={() => {
                setIsRegister(!isRegister);
                setIsForgotPassword(false);
                setError('');
                setSuccessMsg('');
              }}>
                {isForgotPassword || isRegister ? 'Sign In' : 'Register'}
              </button>
            </p>
          </div>
          {onCancel && (
            <div className="landing-back-link" style={{ textAlign: 'center', marginTop: '10px' }}>
              <button type="button" className="link-btn" onClick={onCancel}>
                ← Back to landing page
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

const heroStats = [
  { label: 'Nifty-beating CAGR', value: '25.4%', detail: 'vs. 11.8% Nifty 50 (17y)' },
  { label: 'Signals per week', value: '23', detail: 'Delivered at 4:30PM IST weekdays' },
  { label: 'Accuracy checkpoint', value: '3+ regimes', detail: 'Validated 2008 / 2020 / sideways' },
];

const featureHighlights = [
  {
    title: 'Regime awareness',
    description: 'Blends SMA-200 regime with 0-100 stock scores to skip Risk-Off stretches.',
  },
  {
    title: 'Digital Twin portfolio',
    description: 'Persist your holdings, grade them instantly, and compare risk vs. MRI live signals.',
  },
  {
    title: 'Automated daily digests',
    description: 'SES-powered emails keep you updated without opening the dashboard.',
  },
];

const testimonials = [
  {
    quote: 'MRI delivered an overnight signal I finally trusted. 14-day free trial made it easy to onboard.',
    name: 'Ananya, Retail investor • Bangalore',
  },
  {
    quote: 'Landing page told the story: regime filter + 0-100 score + persistence. Trial let me backtest real portfolios.',
    name: 'Siddharth, Quant analyst • Mumbai',
  },
];

function LandingPage({ onRequestAuth }: { onRequestAuth: () => void }) {
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [status, setStatus] = useState<'idle' | 'success'>('idle');
  const [error, setError] = useState('');

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !phone.trim()) {
      setError('Email and phone are required to reserve the trial.');
      setStatus('idle');
      return;
    }
    setError('');
    setStatus('success');
    onRequestAuth();
  };

  return (
    <div className="landing-shell">
      <div className="landing-header">
        <div className="landing-hero-copy">
          <p className="landing-tagline">Market Regime Intelligence</p>
          <h1>Daily quant signals + portfolio risk visibility for Indian investors.</h1>
          <p className="landing-subtitle">MRI blends regime filtering, 0-100 trend scores, and persistent holdings to keep you aligned with risk-on opportunities.</p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => onRequestAuth()}>Enter the dashboard</button>
            <button className="btn-ghost" onClick={() => onRequestAuth()}>Start risk audit</button>
          </div>
          <div className="hero-meta">
            {heroStats.map(stat => (
              <div key={stat.label} className="hero-stat">
                <strong>{stat.value}</strong>
                <span>{stat.label}</span>
                <small>{stat.detail}</small>
              </div>
            ))}
          </div>
        </div>
        <div className="landing-hero-card">
          <p className="hero-card-title">Reserve your 14-day free trial</p>
          <form className="landing-trial-form" onSubmit={handleSubmit}>
            <label>
              Work email
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@fundelabs.com"
                required
              />
            </label>
            <label>
              Phone / WhatsApp
              <input
                type="tel"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
                required
              />
            </label>
            <button type="submit" className="btn-primary">Reserve free trial</button>
          </form>
          {status === 'success' && (
            <p className="landing-form-status">We locked in the trial. Check your inbox — the login panel is ready.</p>
          )}
          {error && (
            <p className="landing-form-error">{error}</p>
          )}
        </div>
      </div>
      <section className="landing-features">
        {featureHighlights.map(feature => (
          <div key={feature.title} className="feature-card">
            <h3>{feature.title}</h3>
            <p>{feature.description}</p>
          </div>
        ))}
      </section>
      <section className="landing-testimonials">
        {testimonials.map(item => (
          <div key={item.name} className="testimonial-card">
            <p className="testimonial-quote">“{item.quote}”</p>
            <p className="testimonial-name">{item.name}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
/* ─── Reset Password Page ─────────────────────────────────── */
function ResetPasswordPage({ token, onComplete }: { token: string, onComplete: () => void }) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords don't match");
      return;
    }
    setError('');
    setLoading(true);
    try {
      await api.resetPassword(token, password);
      alert('Password successfully reset! Please log in with your new password.');
      onComplete();
    } catch (err: any) {
      setError(err.message || 'Failed to reset password. The link might be expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1 className="brand-title">📊 MRI</h1>
          <p className="brand-subtitle">Market Regime Intelligence</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          <h2 className="form-title">Enter New Password</h2>
          {error && <div className="error-alert">{error}</div>}

          <input type="password" placeholder="New Password" value={password} onChange={e => setPassword(e.target.value)} className="form-input" required minLength={6} />
          <input type="password" placeholder="Confirm New Password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} className="form-input" required minLength={6} />

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Please wait...' : 'Save New Password'}
          </button>

          <div className="toggle-text">
            <button type="button" className="link-btn" onClick={onComplete}>Back to Sign In</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── Regime Card ────────────────────────────────────────── */
function RegimeCard({ regime }: { regime: any }) {
  const colorMap: Record<string, string> = { BULL: '#22c55e', BEAR: '#ef4444', NEUTRAL: '#eab308' };
  const emojiMap: Record<string, string> = { BULL: '🟢', BEAR: '🔴', NEUTRAL: '🟡' };
  const color = colorMap[regime?.regime] || '#6b7280';
  return (
    <div className="card regime-card" style={{ borderLeftColor: color }}>
      <div className="card-label">Market Regime</div>
      <div className="regime-value" style={{ color }}>
        {emojiMap[regime?.regime] || '⚪'} {regime?.regime || 'Loading...'}
      </div>
      <div className="card-meta">
        {regime?.date && <>As of {regime.date} · SMA 200: ₹{regime.sma_200?.toLocaleString()}</>}
      </div>
    </div>
  );
}

/* ─── Daily P&L Summary Card ─────────────────────────────── */
function DailySummaryCard({ summary }: { summary: any }) {
  if (!summary?.has_data) return null;

  return (
    <div className="card daily-summary-card">
      <div className="card-label">Portfolio Summary · {summary.date}</div>
      <div className="summary-stats">
        <div className="summary-stat">
          <span className="summary-label">Total Invested</span>
          <span className="summary-value">₹{summary.total_invested?.toLocaleString()}</span>
        </div>
        <div className="summary-stat">
          <span className="summary-label">Equity</span>
          <span className="summary-value">₹{summary.equity?.toLocaleString()}</span>
        </div>
        <div className="summary-stat">
          <span className="summary-label">Today</span>
          <span className="summary-value" style={{ color: summary.daily_change >= 0 ? '#22c55e' : '#ef4444' }}>
            {summary.daily_change >= 0 ? '+' : ''}₹{summary.daily_change?.toLocaleString()} ({summary.daily_pct}%)
          </span>
        </div>
        <div className="summary-stat">
          <span className="summary-label">Total Return</span>
          <span className="summary-value" style={{ color: summary.total_return >= 0 ? '#22c55e' : '#ef4444' }}>
            {summary.total_return >= 0 ? '+' : ''}₹{summary.total_return?.toLocaleString()} ({summary.total_pct}%)
          </span>
        </div>
        <div className="summary-stat">
          <span className="summary-label">Positions</span>
          <span className="summary-value">{summary.open_positions}</span>
        </div>
      </div>
    </div>
  );
}

/* ─── Execution Dialog ───────────────────────────────────── */
function ExecutionDialog({ signal, totalCapital, onConfirm, onCancel }: {
  signal: any;
  totalCapital: number;
  onConfirm: (price: number, qty: number) => void;
  onCancel: () => void;
}) {
  const allocation = totalCapital * 0.1;
  const suggestedQty = signal.recommended_price ? Math.floor(allocation / signal.recommended_price) : 0;
  const [price, setPrice] = useState(signal.recommended_price?.toString() || '');
  const [qty, setQty] = useState(suggestedQty.toString());

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h3 className="modal-title">
          {signal.action === 'BUY' ? '🟢' : '🔴'} Execute {signal.action}: {signal.symbol}
        </h3>
        <div className="modal-info">
          <div className="info-row">
            <span>10% Allocation:</span>
            <span className="font-bold">₹{allocation.toLocaleString()}</span>
          </div>
          <div className="info-row">
            <span>Recommended Price:</span>
            <span>₹{signal.recommended_price?.toLocaleString()}</span>
          </div>
          <div className="info-row">
            <span>Suggested Qty:</span>
            <span className="font-bold">{suggestedQty} shares</span>
          </div>
        </div>
        <div className="modal-form">
          <label className="modal-label">
            Actual Price (₹)
            <input type="number" value={price} onChange={e => setPrice(e.target.value)} className="form-input" step="0.05" />
          </label>
          <label className="modal-label">
            Quantity
            <input type="number" value={qty} onChange={e => setQty(e.target.value)} className="form-input" min="1" />
          </label>
          {price && qty && (
            <div className="modal-total">
              Total: ₹{(parseFloat(price) * parseInt(qty)).toLocaleString()}
            </div>
          )}
        </div>
        <div className="modal-actions">
          <button className="btn-cancel" onClick={onCancel}>Cancel</button>
          <button className="btn-execute" onClick={() => onConfirm(parseFloat(price), parseInt(qty))}>
            Confirm {signal.action}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Signal Card ────────────────────────────────────────── */
function SignalCard({ signal, totalCapital, onAction, onSelectStock }: {
  signal: any;
  totalCapital: number;
  onAction: (id: string, action: string, price?: number, qty?: number) => void;
  onSelectStock: (stock: any) => void;
}) {
  const [showDialog, setShowDialog] = useState(false);
  const isBuy = signal.action === 'BUY';
  const allocation = totalCapital * 0.1;
  const suggestedQty = signal.recommended_price ? Math.floor(allocation / signal.recommended_price) : 0;
  const isBreakout = signal.conditions?.at_6m_high && signal.conditions?.volume_surge;

  return (
    <>
      <div 
        className={`signal-card ${isBuy ? 'signal-buy' : 'signal-sell'} clickable-row`}
        onClick={() => onSelectStock(signal)}
      >
        <div className="signal-header">
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="signal-symbol">{signal.symbol}</span>
            {isBreakout && <span className="score-trend-indicator" style={{ fontSize: '9px', marginTop: '2px' }}>🚀 BREAKOUT</span>}
          </div>
          <span className={`signal-badge ${isBuy ? 'badge-buy' : 'badge-sell'}`}>{signal.action}</span>
        </div>
        <div className="signal-details">
          <div className="signal-detail"><span className="detail-label">Price</span><span className="detail-value">₹{signal.recommended_price?.toLocaleString()}</span></div>
          <div className="signal-detail"><span className="detail-label">Score</span><span className="detail-value">{signal.score}/100</span></div>
          {isBuy && (
            <div className="signal-detail"><span className="detail-label">Qty</span><span className="detail-value suggested-qty">{suggestedQty} shares (₹{allocation.toLocaleString()})</span></div>
          )}
        </div>
        <div className="signal-reason">{signal.reason}</div>
        {signal.client_action ? (
          <div className={`action-status ${signal.client_action === 'EXECUTED' ? 'status-executed' : 'status-skipped'}`}>
            {signal.client_action === 'EXECUTED' ? '✅ Executed' : '⏭️ Skipped'}
            {signal.actual_price && ` @ ₹${signal.actual_price.toLocaleString()}`}
            {signal.quantity && signal.quantity > 0 && ` × ${signal.quantity}`}
          </div>
        ) : (
          <div className="signal-actions">
            <button className="btn-execute" onClick={() => setShowDialog(true)}>✅ Execute</button>
            <button className="btn-skip" onClick={() => onAction(signal.id, 'SKIPPED')}>⏭️ Skip</button>
          </div>
        )}
      </div>
      {showDialog && (
        <ExecutionDialog
          signal={signal}
          totalCapital={totalCapital}
          onConfirm={(price, qty) => { onAction(signal.id, 'EXECUTED', price, qty); setShowDialog(false); }}
          onCancel={() => setShowDialog(false)}
        />
      )}
    </>
  );
}

/* ─── Add Capital Dialog ─────────────────────────────────── */
function AddCapitalDialog({ onConfirm, onCancel }: {
  onConfirm: (amount: number) => void;
  onCancel: () => void;
}) {
  const [amount, setAmount] = useState('');

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content modal-sm" onClick={e => e.stopPropagation()}>
        <h3 className="modal-title">💰 Add Capital</h3>
        <label className="modal-label">
          Amount (₹)
          <input type="number" value={amount} onChange={e => setAmount(e.target.value)} className="form-input" min="1000" placeholder="e.g. 50000" autoFocus />
        </label>
        <div className="modal-actions">
          <button className="btn-cancel" onClick={onCancel}>Cancel</button>
          <button className="btn-execute" onClick={() => { if (parseFloat(amount) > 0) onConfirm(parseFloat(amount)); }} disabled={!amount || parseFloat(amount) <= 0}>
            Add ₹{amount ? parseFloat(amount).toLocaleString() : '0'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Shadow Momentum Page ────────────────────────────────── */
function ShadowMomentumPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getShadowSignals()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Detecting market momentum...</div>;

  const stocks = data?.stocks || [];

  return (
    <div className="shadow-momentum">
      <h2 className="section-title">🚀 Swing Momentum (Shadow Picks)</h2>
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

      <div className="signals-grid">
        {stocks.map((s: any) => {
          const conditions = {
            ema_50_above_200: s.condition_ema_50_200,
            ema_200_slope_positive: s.condition_ema_200_slope,
            at_6m_high: s.condition_6m_high,
            volume_surge: s.condition_volume,
            relative_strength: s.condition_rs
          };
          const stockWithConditions = { ...s, score: s.total_score, price: s.close, conditions };
          
          return (
            <div 
              key={s.symbol} 
              className={`signal-card ${s.is_breakout ? 'signal-buy' : ''} clickable-row`}
              style={{ borderLeftWidth: s.is_breakout ? '4px' : '1px' }}
              onClick={() => onSelectStock(stockWithConditions)}
            >
              <div className="signal-header">
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span className="signal-symbol">{s.symbol}</span>
                  {s.is_breakout && <span className="score-trend-indicator" style={{ fontSize: '10px', marginTop: '2px', color: '#22c55e', fontWeight: 800 }}>🚀 BREAKOUT</span>}
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

/* ─── Dashboard Page ─────────────────────────────────────── */
function DashboardPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [regime, setRegime] = useState<any>(null);
  const [signals, setSignals] = useState<any>(null);
  const [pending, setPending] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [positions, setPositions] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [showAddCapital, setShowAddCapital] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [r, s, p, sum, prof, pos] = await Promise.all([
        api.getRegime(),
        api.getTodaySignals().catch(() => ({ signals: [] })),
        api.getPendingSignals().catch(() => []),
        api.getDailySummary().catch(() => null),
        api.getProfile().catch(() => null),
        api.getPositions().catch(() => ({ positions: [] })),
      ]);
      setRegime(r);
      setSignals(s);
      setPending(p);
      setSummary(sum);
      setProfile(prof);
      setPositions(pos);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadData(); }, []);

  const handleAction = async (signalId: string, action: string, price?: number, qty?: number) => {
    try {
      const allSignals = [...(pending || []), ...(signals?.signals || [])];
      const sig = allSignals.find((s: any) => s.id === signalId);
      await api.recordAction(signalId, action, price || sig?.recommended_price, qty || 0);
      loadData();
    } catch (err: any) { alert(err.message); }
  };

  const handleAddCapital = async (amount: number) => {
    try {
      await api.addCapital(amount);
      setShowAddCapital(false);
      loadData();
    } catch (err: any) { alert(err.message); }
  };

  if (loading) return <div className="loading">Loading dashboard...</div>;

  const totalCapital = profile?.total_capital || profile?.initial_capital || 100000;

  // Split pending into "older" (not today) signals
  const todayDate = signals?.date;
  const pendingOlder = (pending || []).filter((s: any) => s.date !== todayDate);
  const todaySignals = signals?.signals || [];

  return (
    <div className="dashboard">
      <div className="dashboard-top-row">
        <RegimeCard regime={regime} />
        <div className="card capital-card">
          <div className="card-label">Total Portfolio Value</div>
          <div className="capital-value">₹{(summary?.equity || totalCapital).toLocaleString()}</div>
          <div className="card-meta">
            Invested Amount: ₹{(summary?.total_invested || totalCapital).toLocaleString()}
          </div>
          <button className="btn-add-capital" onClick={() => setShowAddCapital(true)}>+ Add Capital</button>
        </div>
      </div>

      <DailySummaryCard summary={summary} />

      {/* ── SECTION 0: My Positions (Core + External) ── */}
      {positions?.positions?.length > 0 ? (
        <section className="section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 className="section-title" style={{ margin: 0 }}>📦 My Holdings</h2>
            <button
              className="btn-secondary"
              onClick={() => { setLoading(true); loadData(); }}
              style={{ padding: '6px 12px', fontSize: '13px' }}
            >
              🔄 Refresh
            </button>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr><th>Symbol</th><th>Source</th><th>Price</th><th>Qty</th><th>Value</th><th>P&L %</th></tr>
              </thead>
              <tbody>
                {positions.positions.map((p: any) => (
                  <tr key={`${p.source}-${p.symbol}`} onClick={() => onSelectStock(p)} className="clickable-row">
                    <td className="font-bold">
                      {p.symbol}
                      {p.conditions?.at_6m_high && p.conditions?.volume_surge && (
                        <div className="score-trend-indicator" style={{ fontSize: '9px', fontWeight: 'normal' }}>🚀 BREAKOUT</div>
                      )}
                    </td>
                    <td>
                      <span className={`action-badge ${p.source === 'Core' ? 'badge-executed' : 'badge-skipped'}`} style={{ fontSize: '10px' }}>
                        {p.source}
                      </span>
                    </td>
                    <td>₹{p.current_price?.toLocaleString()}</td>
                    <td>{p.quantity}</td>
                    <td className="font-medium">₹{((p.current_price || 0) * (p.quantity || 0)).toLocaleString()}</td>
                    <td style={{ color: (p.pnl_pct || 0) >= 0 ? '#22c55e' : '#ef4444' }}>
                      <div className="score-cell">
                        {p.score !== undefined && <span className="score-badge">{p.score}</span>}
                        {p.pnl_pct}%
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <section className="section">
          <div className="empty-state">
            No active holdings detected. Upload your portfolio in <strong>Risk Audit</strong> to see your unified wealth here.
          </div>
        </section>
      )}

      {/* ── SECTION 1: Pending Trades (from previous days) ── */}
      {pendingOlder.length > 0 && (
        <section className="section pending-section">
          <h2 className="section-title pending-title">
            ⏳ Pending — Execute Your Trades
          </h2>
          <p className="section-subtitle">
            You received these signals earlier. Mark them as Executed (with actual price + qty from your broker) or Skip.
          </p>
          <div className="signals-grid">
            {pendingOlder.map((s: any) => (
              <SignalCard key={s.id} signal={s} totalCapital={totalCapital} onAction={handleAction} onSelectStock={onSelectStock} />
            ))}
          </div>
        </section>
      )}

      {/* ── SECTION 2: Today's Fresh Signals ── */}
      <section className="section">
        <h2 className="section-title today-title">
          📊 Today's New Signals {todayDate ? `(${todayDate})` : ''}
        </h2>
        <p className="section-subtitle">
          Fresh signals from today's pipeline. Execute these in your broker tomorrow at 9:15 AM.
        </p>
        {todaySignals.length > 0 ? (
          <div className="signals-grid">
            {todaySignals.map((s: any) => (
              <SignalCard key={s.id} signal={s} totalCapital={totalCapital} onAction={handleAction} onSelectStock={onSelectStock} />
            ))}
          </div>
        ) : (
          <div className="empty-state">No new signals today. The market may be closed or there are no actionable setups.</div>
        )}
      </section>

      {showAddCapital && (
        <AddCapitalDialog onConfirm={handleAddCapital} onCancel={() => setShowAddCapital(false)} />
      )}
    </div>
  );
}

/* ─── History Page ────────────────────────────────────────── */
function HistoryPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [actions, setActions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getActionHistory()
      .then(setActions)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading history...</div>;

  return (
    <div className="history">
      <h2 className="section-title">My Trade History</h2>
      {actions.length > 0 ? (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Symbol</th>
                <th>Signal</th>
                <th>Action</th>
                <th>Rec. Price</th>
                <th>Actual Price</th>
                <th>Qty</th>
                <th>Score</th>
                <th>Regime</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((a: any) => (
                <tr key={a.id} onClick={() => onSelectStock(a)} className="clickable-row">
                  <td>{a.signal_date}</td>
                  <td className="font-bold">{a.symbol}</td>
                  <td><span className={`signal-badge-sm ${a.signal_action === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>{a.signal_action}</span></td>
                  <td><span className={`action-badge ${a.action_taken === 'EXECUTED' ? 'badge-executed' : 'badge-skipped'}`}>{a.action_taken}</span></td>
                  <td>₹{a.recommended_price?.toLocaleString()}</td>
                  <td>₹{a.actual_price?.toLocaleString()}</td>
                  <td>{a.quantity || '-'}</td>
                  <td>{a.score}/100</td>
                  <td>{a.regime}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">No actions recorded yet. Start by executing or skipping signals on the Dashboard.</div>
      )}
    </div>
  );
}

/* ─── Performance Page ────────────────────────────────────── */
function PerformancePage() {
  const [performance, setPerformance] = useState<any>(null);
  const [positions, setPositions] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getPerformance().catch(() => null),
      api.getPositions().catch(() => ({ positions: [] })),
    ]).then(([perf, pos]) => {
      setPerformance(perf);
      setPositions(pos);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading performance...</div>;

  // Merge client + nifty data for charting
  const chartData = performance?.client?.map((c: any, i: number) => ({
    date: c.date,
    'Your Portfolio': c.value,
    'Nifty 50': performance.nifty?.[i]?.value || 100,
  })) || [];

  return (
    <div className="performance">
      <h2 className="section-title">My Performance</h2>

      {performance?.initial_capital && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-label">Initial Capital</div>
            <div className="stat-value">₹{performance.initial_capital.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Current Equity</div>
            <div className="stat-value" style={{ color: performance.latest_equity >= performance.initial_capital ? '#22c55e' : '#ef4444' }}>
              ₹{performance.latest_equity.toLocaleString()}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Open Positions</div>
            <div className="stat-value">{positions?.count || 0}</div>
          </div>
        </div>
      )}

      {chartData.length > 0 ? (
        <div className="chart-container">
          <h3 className="chart-title">Your Equity vs Nifty 50 (Base 100)</h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: 8, color: '#f1f5f9' }} />
              <Legend />
              <Line type="monotone" dataKey="Your Portfolio" stroke="#3b82f6" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Nifty 50" stroke="#6b7280" strokeWidth={1.5} dot={false} strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="empty-state">No equity data yet. Execute some signals to start tracking your performance.</div>
      )}

      {positions?.positions?.length > 0 && (
        <section className="section">
          <h3 className="section-title">Current Positions (Core + External)</h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr><th>Symbol</th><th>Source</th><th>Entry Date</th><th>Entry Price</th><th>Current Price</th><th>Qty</th><th>P&L %</th></tr>
              </thead>
              <tbody>
                {positions.positions.map((p: any) => (
                  <tr key={`${p.source}-${p.symbol}`}>
                    <td className="font-bold">{p.symbol}</td>
                    <td>
                      <span className={`action-badge ${p.source === 'Core' ? 'badge-executed' : 'badge-skipped'}`} style={{ fontSize: '10px' }}>
                        {p.source}
                      </span>
                    </td>
                    <td>{p.entry_date}</td>
                    <td>₹{p.entry_price?.toLocaleString()}</td>
                    <td>₹{p.current_price?.toLocaleString()}</td>
                    <td>{p.quantity}</td>
                    <td style={{ color: (p.pnl_pct || 0) >= 0 ? '#22c55e' : '#ef4444' }}>{p.pnl_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

/* ─── Risk Audit Page ────────────────────────────────────── */
function RiskAuditPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [savedResult, setSavedResult] = useState<any>(null);
  const [savedError, setSavedError] = useState('');
  const [holdingsStatus, setHoldingsStatus] = useState<any>(null);
  const [holdingsStatusLoading, setHoldingsStatusLoading] = useState(false);
  const [error, setError] = useState('');
  const [saveLoading, setSaveLoading] = useState(false);
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);
  const [savedSortConfig, setSavedSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);
  const [deleteAllArmed, setDeleteAllArmed] = useState(false);

  const [savedLoading, setSavedLoading] = useState(false);

  const loadHoldingsStatus = async () => {
    setHoldingsStatusLoading(true);
    try {
      const data = await api.getHoldingsStatus();
      setHoldingsStatus(data);
    } catch (err: any) {
      setHoldingsStatus({ storage_ready: false, error: err?.message || 'Failed to load holdings status' });
    } finally {
      setHoldingsStatusLoading(false);
    }
  };

  const loadSavedHoldings = async () => {
    setSavedLoading(true);
    try {
      setSavedError('');
      const data = await api.getSavedHoldings();
      setSavedResult(data);
    } catch (err: any) {
      console.error('Failed to load saved holdings', err);
      setSavedResult(null);
      setSavedError(err?.message || 'Failed to load saved holdings');
    } finally {
      setSavedLoading(false);
    }
  };

  useEffect(() => {
    loadSavedHoldings();
    loadHoldingsStatus();
  }, []);

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const handleSavedSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (savedSortConfig && savedSortConfig.key === key && savedSortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSavedSortConfig({ key, direction });
  };

  const getSortIcon = (key: string) => {
    if (!sortConfig || sortConfig.key !== key) return ' ↕️';
    return sortConfig.direction === 'asc' ? ' 🔼' : ' 🔽';
  };

  const getSavedSortIcon = (key: string) => {
    if (!savedSortConfig || savedSortConfig.key !== key) return ' ↕️';
    return savedSortConfig.direction === 'asc' ? ' 🔼' : ' 🔽';
  };

  const getEffectiveCurrentPrice = (h: any) => {
    const live = h?.live_price;
    const eod = h?.current_price;
    const cost = h?.avg_cost;
    return (live ?? eod ?? cost ?? null);
  };

  const getSortableValue = (row: any, key: string) => {
    if (!row) return null;
    switch (key) {
      case 'current_effective':
        return getEffectiveCurrentPrice(row);
      case 'below_200ema':
        return row?.below_200ema === true ? 1 : (row?.below_200ema === false ? 0 : null);
      default:
        return row[key];
    }
  };

  const sortedHoldings = useMemo(() => {
    if (!result?.holdings) return [];
    let sortableItems = [...result.holdings];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        let aVal = getSortableValue(a, sortConfig.key);
        let bVal = getSortableValue(b, sortConfig.key);
        
        if (aVal === null || aVal === undefined) aVal = sortConfig.direction === 'asc' ? Infinity : -Infinity;
        if (bVal === null || bVal === undefined) bVal = sortConfig.direction === 'asc' ? Infinity : -Infinity;
        
        if (typeof aVal === 'string') aVal = aVal.toLowerCase();
        if (typeof bVal === 'string') bVal = bVal.toLowerCase();

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortableItems;
  }, [result?.holdings, sortConfig]);

  const sortedSavedHoldings = useMemo(() => {
    if (!savedResult?.holdings) return [];
    let sortableItems = [...savedResult.holdings];
    if (savedSortConfig !== null) {
      sortableItems.sort((a, b) => {
        let aVal = getSortableValue(a, savedSortConfig.key);
        let bVal = getSortableValue(b, savedSortConfig.key);

        if (aVal === null || aVal === undefined) aVal = savedSortConfig.direction === 'asc' ? Infinity : -Infinity;
        if (bVal === null || bVal === undefined) bVal = savedSortConfig.direction === 'asc' ? Infinity : -Infinity;

        if (typeof aVal === 'string') aVal = aVal.toLowerCase();
        if (typeof bVal === 'string') bVal = bVal.toLowerCase();

        if (aVal < bVal) return savedSortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return savedSortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortableItems;
  }, [savedResult?.holdings, savedSortConfig]);

  const [dragging, setDragging] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.uploadPortfolioCsv(file);

      // ── Immediately show analysis if the server returned it ──
      if (data?.analysis) {
        setResult(data.analysis);
      }

      await loadSavedHoldings();
      await loadHoldingsStatus();

      const persisted = (data?.digital_twin_row_count !== undefined && data?.digital_twin_row_count !== null)
        ? ` (Saved: ${data.digital_twin_row_count} holdings)` : '';

      const pending = data?.pending_symbols?.length > 0
        ? `\n\n⏳ ${data.pending_symbols.length} unknown symbol(s) queued for scoring: ${data.pending_symbols.slice(0,5).join(', ')}${data.pending_symbols.length > 5 ? '...' : ''}. Scores will appear after the next pipeline run.`
        : '';

      if (data?.digital_twin_saved) {
        alert(`✅ Portfolio uploaded and analysed!${persisted}${pending}`);
      } else {
        const extra = data?.digital_twin_error ? `\n\nSave failed: ${data.digital_twin_error}` : '';
        alert(`Portfolio uploaded and analysed, but could not save holdings to your Digital Twin.${extra}${pending}`);
      }
    } catch (err: any) {
      setError(err.message === 'Failed to fetch'
        ? '⚠️ Connection Failed: Please ensure you have "Clear Cache & Re-deployed" on Render and your VITE_API_URL is correct.'
        : (err.message || 'Failed to analyze portfolio'));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToHoldings = async () => {
    if (!result?.holdings) return;
    setSaveLoading(true);
    try {
      const holdingsToSave = result.holdings.map((h: any) => ({
        symbol: h.symbol,
        quantity: h.quantity,
        avg_cost: h.avg_cost
      }));
      
      const resp = await api.saveHoldingsBulk(holdingsToSave);
      const persisted = resp?.persisted_holdings_count !== undefined ? ` (Persisted: ${resp.persisted_holdings_count})` : '';
      
      alert(`Success: ${holdingsToSave.length} holdings saved to your Digital Twin!${persisted}`);
      loadSavedHoldings();
      loadHoldingsStatus();
    } catch (err: any) {
      console.error('Save failed:', err);
      alert(err.message || 'Failed to save holdings to database');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleDeleteHolding = async (symbol: string) => {
    if (!confirm(`Remove ${symbol} from your holdings?`)) return;
    try {
      await api.deleteHolding(symbol);
      loadSavedHoldings();
      loadHoldingsStatus();
    } catch (err: any) {
      alert(err.message || 'Failed to delete holding');
    }
  };

	  const handleDeleteAllHoldings = async () => {
	    if (!deleteAllArmed) {
	      setDeleteAllArmed(true);
	      window.setTimeout(() => setDeleteAllArmed(false), 8000);
	      return;
	    }
	    try {
	      const resp = await api.deleteAllHoldings();
	      const persisted = resp?.persisted_holdings_count !== undefined ? `Remaining: ${resp.persisted_holdings_count}` : '';
	      alert(`Holdings deleted. ${persisted}`.trim());
	      loadSavedHoldings();
	      loadHoldingsStatus();
	      setDeleteAllArmed(false);
	    } catch (err: any) {
	      setDeleteAllArmed(false);
	      alert(err.message || 'Failed to delete holdings');
	    }
	  };

	  const handleRegradeHoldings = async () => {
	    try {
	      const sendEmail = confirm('Email you the updated Risk Audit report after regrading?');
	      setSavedLoading(true);
	      const data = await api.regradeHoldingsSync(sendEmail);
	      setSavedResult(data);
	      await loadHoldingsStatus();
	      alert(`Regrade complete. ${sendEmail ? 'If SES is configured, you should also receive an email.' : ''}`.trim());
	    } catch (err: any) {
	      alert(err.message || 'Failed to start regrade');
	    }
	    finally {
	      setSavedLoading(false);
	    }
	  };

	  const hasSavedHoldings = !!(savedResult && savedResult.holdings && savedResult.holdings.length > 0);
	  const canDeleteSavedHoldings = (holdingsStatus?.holdings_count ?? 0) > 0 || hasSavedHoldings;

    // Manual Add States
    const [manualSym, setManualSym] = useState('');
    const [manualQty, setManualQty] = useState('');
    const [manualCost, setManualCost] = useState('');
    const [manualSuggs, setManualSuggs] = useState<any[]>([]);

    useEffect(() => {
        const timer = setTimeout(async () => {
            if (manualSym.length >= 2) {
                try {
                    const results = await api.searchStocks(manualSym);
                    setManualSuggs(results || []);
                } catch (e) {
                    setManualSuggs([]);
                }
            } else {
                setManualSuggs([]);
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [manualSym]);

    const handleManualAdd = async () => {
        if (!manualSym || !manualQty || !manualCost) {
            alert('Please fill out all fields: Symbol, Quantity, and Avg Cost');
            return;
        }
        try {
            setLoading(true);
            await api.addHolding(manualSym, parseFloat(manualQty), parseFloat(manualCost));
            setManualSym(''); setManualQty(''); setManualCost('');
            loadSavedHoldings();
            loadHoldingsStatus();
        } catch (err: any) {
            alert(err.message || 'Failed to add holding');
        } finally {
            setLoading(false);
        }
    };

	  const uploadPanel = (
	    <div className="upload-section animate-fade-in">
	      <div 
	        className={`upload-zone ${dragging ? 'dragging' : ''}`}
	        onDragOver={handleDragOver}
	        onDragLeave={handleDragLeave}
	        onDrop={handleDrop}
	        onClick={() => document.getElementById('csv-upload')?.click()}
	      >
	        <div className="upload-icon">📂</div>
	        <div className="upload-text">
	          <span className="upload-main-text">
	            {file ? file.name : 'Click or Drag CSV here'}
	          </span>
	          <span className="upload-sub-text">
	            Supports Zerodha, Groww, and standard portfolio CSVs.
	          </span>
            <div className="info-shelf" style={{ marginTop: '12px', padding: '10px', background: '#f8fafc', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.8rem', color: '#64748b' }}>
               <strong>💡 Required Columns:</strong> <code>symbol</code>, <code>quantity</code>, <code>avg_cost</code>
            </div>
	        </div>
	        <input 
	          type="file" 
	          accept=".csv" 
	          onChange={handleFileChange} 
	          className="file-input"
	          id="csv-upload"
	        />
	      </div>

	      <div className="upload-actions">
	        <button 
	          className="btn-upload-submit" 
	          onClick={handleUpload} 
	          disabled={!file || loading}
	        >
	          {loading ? '🔬 Analyzing Portfolio...' : (hasSavedHoldings ? 'Upload / Replace Portfolio' : 'Analyze Risk Now')}
	        </button>
	        
	        {file && !loading && (
	          <button className="link-btn" onClick={() => setFile(null)}>
	            Clear selection
	          </button>
	        )}
	      </div>
	    </div>
	  );

	  const savedHoldingsSection = (
	    <section className="section" style={{ marginTop: hasSavedHoldings ? '16px' : '40px' }}>
	      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
	        <h2 className="section-title" style={{ margin: 0 }}>🛡️ My Holdings (Digital Twin)</h2>
	        {canDeleteSavedHoldings && (
	          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
	            <button className="btn-secondary" onClick={handleRegradeHoldings} disabled={savedLoading} style={{ padding: '8px 12px' }}>
	              {savedLoading ? '🔄 Regrading...' : '🔄 Regrade Holdings'}
	            </button>
	            {deleteAllArmed && (
	              <div style={{ color: '#fecaca', fontSize: '12px', fontWeight: 700 }}>
	                Click again to permanently delete all holdings
	              </div>
	            )}
	            <button className="btn-danger" onClick={handleDeleteAllHoldings} style={{ padding: '8px 12px' }}>
	              {deleteAllArmed ? '⚠️ Confirm Delete All' : '🗑️ Delete Saved Portfolio'}
	            </button>
	            {deleteAllArmed && (
	              <button className="link-btn" onClick={() => setDeleteAllArmed(false)}>
	                Cancel
	              </button>
	            )}
	          </div>
	        )}
	      </div>
	      <p className="section-subtitle">
	        Your persistent portfolio layer. These assets are tracked in real-time against MRI intelligence.
	      </p>

	      <div className="stats-row" style={{ marginTop: '12px' }}>
	        <div className="stat-card" style={{ flex: 1 }}>
	          <div className="stat-label">Storage Status</div>
	          <div className="card-meta" style={{ marginTop: '8px', lineHeight: 1.5 }}>
	            {holdingsStatusLoading ? (
	              <span>Checking…</span>
	            ) : holdingsStatus ? (
	              <>
	                <div><b>storage_ready</b>: {String(!!holdingsStatus.storage_ready)}</div>
	                {holdingsStatus.client_id && <div><b>client_id</b>: <span style={{ fontFamily: 'monospace' }}>{holdingsStatus.client_id}</span></div>}
	                {holdingsStatus.database && <div><b>database</b>: <span style={{ fontFamily: 'monospace' }}>{holdingsStatus.database}</span></div>}
	                  {holdingsStatus.holdings_count !== undefined && holdingsStatus.holdings_count !== null && (
	                    <div><b>holdings_count</b>: {holdingsStatus.holdings_count}</div>
	                  )}
	                  {holdingsStatus.ungraded_symbols_count !== undefined && holdingsStatus.ungraded_symbols_count !== null && (
	                    <div><b>ungraded_symbols_count</b>: {holdingsStatus.ungraded_symbols_count}</div>
	                  )}
	                  {holdingsStatus.error && (
	                    <div style={{ color: '#ef4444', marginTop: '6px' }}><b>error</b>: {String(holdingsStatus.error)}</div>
	                  )}
	                </>
	              ) : (
	              <span>Not available</span>
	            )}
	          </div>
	        </div>
	      </div>

	      {savedLoading ? (
	        <div className="loading">📡 Loading your Digital Twin...</div>
	      ) : savedError ? (
	        <div className="empty-state">⚠️ Could not load your Digital Twin: {savedError}</div>
	      ) : savedResult && savedResult.storage_ready === false ? (
	        <div className="empty-state">⚠️ Holdings storage not ready yet: {savedResult.summary || savedResult.error || 'Unknown error'}</div>
	      ) : hasSavedHoldings ? (
	        <>
	          {savedResult.analysis_error && (
	            <div className="empty-state" style={{ marginBottom: '12px' }}>
	              ⚠️ MRI analysis is falling back (scores may be missing): {String(savedResult.analysis_error)}
	            </div>
	          )}
	          {savedResult.pricing_note && (
	            <div className="empty-state" style={{ marginBottom: '12px' }}>{savedResult.pricing_note}</div>
	          )}
	          <div className="stats-row">
	            <div className="stat-card" style={{ borderLeft: `4px solid ${savedResult.risk_level === 'EXTREME' || savedResult.risk_level === 'HIGH' ? '#ef4444' : savedResult.risk_level === 'MODERATE' ? '#eab308' : '#22c55e'}` }}>
	              <div className="stat-label">Portfolio Risk</div>
	              <div className="stat-value">{savedResult.risk_level}</div>
	              <div className="card-meta">Score: {savedResult.risk_score_pct || '0%'}</div>
	            </div>
	            <div className="stat-card">
	              <div className="stat-label">Invested Value</div>
	              <div className="stat-value">₹{savedResult.total_portfolio_value?.toLocaleString()}</div>
	            </div>
	            <div className="stat-card">
	              <div className="stat-label">Holdings</div>
	              <div className="stat-value">{savedResult.holdings_count}</div>
	            </div>
	          </div>

	          <div className="table-container" style={{ marginTop: '24px' }}>
	            <table className="data-table">
	              <thead>
	                <tr>
	                  <th onClick={() => handleSavedSort('symbol')} style={{cursor: 'pointer', userSelect: 'none'}}>Symbol{getSavedSortIcon('symbol')}</th>
	                  <th onClick={() => handleSavedSort('score')} style={{cursor: 'pointer', userSelect: 'none'}}>Score{getSavedSortIcon('score')}</th>
	                  <th onClick={() => handleSavedSort('alignment')} style={{cursor: 'pointer', userSelect: 'none'}}>Alignment{getSavedSortIcon('alignment')}</th>
	                  <th onClick={() => handleSavedSort('quantity')} style={{cursor: 'pointer', userSelect: 'none'}}>Qty{getSavedSortIcon('quantity')}</th>
	                  <th onClick={() => handleSavedSort('avg_cost')} style={{cursor: 'pointer', userSelect: 'none'}}>Avg Cost{getSavedSortIcon('avg_cost')}</th>
	                  <th onClick={() => handleSavedSort('current_effective')} style={{cursor: 'pointer', userSelect: 'none'}}>Current{getSavedSortIcon('current_effective')}</th>
	                  <th onClick={() => handleSavedSort('pnl_pct')} style={{cursor: 'pointer', userSelect: 'none'}}>P&L %{getSavedSortIcon('pnl_pct')}</th>
	                  <th onClick={() => handleSavedSort('risk_contribution_pct')} style={{cursor: 'pointer', userSelect: 'none'}}>Risk Contrib{getSavedSortIcon('risk_contribution_pct')}</th>
	                  <th>Actions</th>
	                </tr>
	              </thead>
	              <tbody>
	                {sortedSavedHoldings.map((h: any) => (
	                  <tr key={h.symbol}>
	                    <td className="font-bold">{h.symbol}</td>
	                    <td>{h.score !== null ? `${h.score}/100` : 'N/A'}</td>
	                    <td>
	                      <span className={`action-badge ${h.alignment === 'ALIGNED' || h.alignment === 'STRONG' ? 'badge-executed' : h.alignment === 'WEAK' ? 'badge-skipped' : ''}`}>
	                        {h.alignment}
	                      </span>
	                    </td>
	                    <td>{h.quantity}</td>
	                    <td>₹{h.avg_cost?.toLocaleString()}</td>
	                    <td>
	                      {(() => {
	                        const p = getEffectiveCurrentPrice(h);
	                        const label = h.live_price ? 'LIVE (Yahoo)' : (h.current_price ? 'EOD (DB)' : (h.avg_cost ? 'COST' : 'N/A'));
	                        return (
	                          <>
	                            ₹{p !== null && p !== undefined ? Number(p).toLocaleString() : 'N/A'}
	                            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>{label}</div>
	                          </>
	                        );
	                      })()}
	                    </td>
	                    <td style={{ color: (h.pnl_pct || 0) >= 0 ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
	                      {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct}%
	                    </td>
	                    <td>{h.risk_contribution_pct}%</td>
	                    <td>
	                      <button className="btn-danger" onClick={() => handleDeleteHolding(h.symbol)} style={{ padding: '4px 8px', fontSize: '12px' }}>
	                        🗑️ Remove
	                      </button>
	                    </td>
	                  </tr>
	                ))}
	              </tbody>
	            </table>
	          </div>
	        </>
	      ) : (
	        <div className="empty-state">There are no stocks in your portfolio to track here right now. When you add, it will be displayed.</div>
	      )}
	    </section>
	  );

	  return (
	    <div className="risk-audit">
	      <h2 className="section-title">Portfolio Risk Audit</h2>
	      <p className="section-subtitle">
	        Upload your broker holdings CSV (e.g., Zerodha) to instantly analyze your portfolio's risk against our MRI framework.
	      </p>

	      {hasSavedHoldings && savedHoldingsSection}
	      {!hasSavedHoldings && uploadPanel}
	      {hasSavedHoldings && (
	        <div style={{ marginTop: '18px' }}>
	          <div className="empty-state" style={{ marginBottom: '10px' }}>
	            Upload a new CSV below to replace/analyze your portfolio.
	          </div>
	          {uploadPanel}
	        </div>
	      )}
	
	      {result && (
	        <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
	          <button 
            className="btn-secondary" 
            onClick={handleSaveToHoldings}
            disabled={saveLoading}
            style={{ backgroundColor: '#059669', color: 'white' }}
          >
            {saveLoading ? 'Saving...' : '💾 Save to My Holdings'}
          </button>
          <button 
            className="btn-secondary" 
            onClick={() => setResult(null)}
          >
            ❌ Clear Result
          </button>
        </div>
      )}

      {error && <div className="error-alert" style={{ marginTop: '16px' }}>{error}</div>}

      {result && result.async_processing && result.missing_symbols && result.missing_symbols.length > 0 && (
        <div className="card" style={{ marginTop: '24px', backgroundColor: '#1e3a8a', borderColor: '#3b82f6', borderLeft: '4px solid #60a5fa' }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '15px', color: '#93c5fd' }}>Data Discovery in Progress 🕵️‍♂️</h3>
          <p style={{ margin: 0, fontSize: '14px', color: '#bfdbfe', lineHeight: 1.5 }}>
            Note: We are currently downloading deep historical data for: <strong>{result.missing_symbols.join(', ')}</strong>.<br/>
            You will receive an updated, complete portfolio risk report via email in approx 20 minutes once the data is ingested and scored.<br/>
            In the meantime, here is the partial diagnosis for your recognized holdings:
          </p>
        </div>
      )}

	      {result && result.holdings && (
	        <div className="audit-results animate-fade-in" style={{ marginTop: '24px' }}>
	          {result.pricing_note && (
	            <div className="empty-state" style={{ marginBottom: '12px' }}>{result.pricing_note}</div>
	          )}
          <div className="stats-row">
            <div className="stat-card" style={{ borderLeft: `4px solid ${result.risk_level === 'EXTREME' || result.risk_level === 'HIGH' ? '#ef4444' : result.risk_level === 'MODERATE' ? '#eab308' : '#22c55e'}` }}>
              <div className="stat-label">Result Risk</div>
              <div className="stat-value">{result.risk_level}</div>
              <div className="card-meta">Score: {result.risk_score_pct}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Market Regime</div>
              <div className="stat-value">{result.regime}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Invested Value</div>
              <div className="stat-value">₹{result.total_portfolio_value?.toLocaleString()}</div>
            </div>
          </div>

          <div className="card summary-card" style={{ marginTop: '16px', backgroundColor: '#1e293bcc', padding: '16px', borderRadius: '8px' }}>
            <h3 style={{ fontSize: '16px', marginBottom: '8px', color: '#e2e8f0' }}>Diagnosis</h3>
            <p style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.5' }}>{result.risk_level_description}</p>
            <p style={{ color: '#cbd5e1', fontSize: '15px', marginTop: '12px' }}>{result.summary}</p>
          </div>

          <section className="section" style={{ marginTop: '24px' }}>
            <h3 className="section-title">Holding Breakdown</h3>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th title="The stock symbol or ticker name" onClick={() => handleSort('symbol')} style={{cursor: 'pointer', userSelect: 'none'}}>Symbol{getSortIcon('symbol')}</th>
                    <th title="The MRI trend score (0-100) combining moving averages, momentum, and volume" onClick={() => handleSort('score')} style={{cursor: 'pointer', userSelect: 'none'}}>Score (0-100){getSortIcon('score')}</th>
                    <th title="Whether the stock's trend aligns with the overall Market Regime" onClick={() => handleSort('alignment')} style={{cursor: 'pointer', userSelect: 'none'}}>Alignment{getSortIcon('alignment')}</th>
                    <th title="Percentage of your total portfolio value invested in this stock" onClick={() => handleSort('weight_pct')} style={{cursor: 'pointer', userSelect: 'none'}}>Weight{getSortIcon('weight_pct')}</th>
                    <th title="How much of your portfolio's total risk comes from this specific holding" onClick={() => handleSort('risk_contribution_pct')} style={{cursor: 'pointer', userSelect: 'none'}}>Risk Contribution{getSortIcon('risk_contribution_pct')}</th>
                    <th title="Latest price used for display: Live Yahoo if available, else EOD DB close, else your avg cost" onClick={() => handleSort('current_effective')} style={{cursor: 'pointer', userSelect: 'none'}}>Current{getSortIcon('current_effective')}</th>
                    <th title="WARNING: Stocks trading below their 200-day Exponential Moving Average are in long-term downtrends" onClick={() => handleSort('below_200ema')} style={{cursor: 'pointer', userSelect: 'none'}}>Below 200 EMA{getSortIcon('below_200ema')}</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedHoldings.map((h: any) => (
                    <tr key={h.symbol} onClick={() => onSelectStock(h)} className="clickable-row">
                      <td className="font-bold">{h.symbol}</td>
                      <td>{h.score !== null ? `${h.score}/100` : 'N/A'}</td>
                      <td>
                        <span className={`action-badge ${h.alignment === 'ALIGNED' || h.alignment === 'STRONG' ? 'badge-executed' : h.alignment === 'WEAK' ? 'badge-skipped' : ''}`}>
                          {h.alignment}
                        </span>
                      </td>
                      <td>{h.weight_pct}%</td>
                      <td>{h.risk_contribution_pct}%</td>
                      <td>
                        {(() => {
                          const p = getEffectiveCurrentPrice(h);
                          const label = h.live_price ? 'LIVE (Yahoo)' : (h.current_price ? 'EOD (DB)' : (h.avg_cost ? 'COST' : 'N/A'));
                          return (
                            <>
                              ₹{p !== null && p !== undefined ? Number(p).toLocaleString() : 'N/A'}
                              <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>{label}</div>
                            </>
                          );
                        })()}
                      </td>
                      <td>
                        {h.score === null ? 'N/A' : (h.below_200ema ? <span style={{color: '#ef4444'}}>⚠️ YES</span> : 'NO')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
	      )}

        <section className="section" style={{ marginTop: '24px', backgroundColor: '#fdfcfe', padding: '1.5rem', borderRadius: '12px', border: '1px solid #e9d5ff' }}>
            <h3 className="section-title">✨ Add Core Holding Manually</h3>
            <p className="section-subtitle">No CSV? No problem. Add your 20+ stocks one-by-one with 100% precision.</p>
            
            <div className="manual-entry-bar" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '12px' }}>
                <div style={{ position: 'relative', flex: 2, minWidth: '200px' }}>
                    <input 
                        type="text" placeholder="Symbol (e.g. RELIANCE)" 
                        value={manualSym} onChange={e => setManualSym(e.target.value)} 
                        className="form-input" style={{ marginBottom: 0 }}
                    />
                    {manualSuggs.length > 0 && (
                        <div className="autocomplete-dropdown" style={{ 
                            position: 'absolute', top: '100%', left: 0, right: 0, 
                            backgroundColor: 'white', border: '1px solid #e2e8f0', 
                            borderRadius: '8px', zIndex: 1000, marginTop: '4px', maxHeight: '160px', overflowY: 'auto'
                        }}>
                            {manualSuggs.map(s => (
                                <div key={s.symbol} onClick={() => { setManualSym(s.symbol); setManualSuggs([]); }} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid #f1f5f9' }}>
                                    <span style={{ fontWeight: 700 }}>{s.symbol}</span> <span style={{ fontSize: '0.8rem', color: '#64748b' }}>{s.company_name}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                <input type="number" placeholder="Qty" value={manualQty} onChange={e => setManualQty(e.target.value)} className="form-input" style={{ flex: 1, marginBottom: 0, minWidth: '80px' }} />
                <input type="number" placeholder="Avg Cost" value={manualCost} onChange={e => setManualCost(e.target.value)} className="form-input" style={{ flex: 1, marginBottom: 0, minWidth: '100px' }} />
                <button className="btn-primary" onClick={handleManualAdd} style={{ padding: '8px 20px', whiteSpace: 'nowrap' }}>Add to Portfolio</button>
            </div>
        </section>

	      {!hasSavedHoldings && savedHoldingsSection}
	    </div>
	  );
	}

/* ─── Watchlist Page ─────────────────────────────────────── */
function WatchlistPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSymbol, setNewSymbol] = useState('');
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [error, setError] = useState('');

  // Search Logic for Autocomplete
  useEffect(() => {
    const timer = setTimeout(async () => {
        if (newSymbol.length >= 2) {
            try {
                const results = await api.searchStocks(newSymbol);
                setSuggestions(results || []);
            } catch (e) {
                setSuggestions([]);
            }
        } else {
            setSuggestions([]);
        }
    }, 300); // Debounce
    return () => clearTimeout(timer);
  }, [newSymbol]);

  const loadWatchlist = async () => {
    try {
      const data = await api.getWatchlist();
      setWatchlist(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWatchlist();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) return;
    setError('');
    
    // OPTIMISTIC UPDATE: Add to local state immediately
    const optimisticItem = { symbol, price: null, score: null, trend_alignment: null, is_pending: true };
    setWatchlist(prev => [optimisticItem, ...prev]);
    setNewSymbol('');
    setSuggestions([]);

    try {
      await api.addToWatchlist(symbol);
      loadWatchlist();
    } catch (err: any) {
      setError(err.message || 'Failed to add symbol');
      // Rollback on error
      setWatchlist(prev => prev.filter(item => item.symbol !== symbol));
    }
  };

  const handleRemove = async (symbol: string) => {
    if (!confirm(`Remove ${symbol} from watchlist?`)) return;
    try {
      await api.removeFromWatchlist(symbol);
      loadWatchlist();
    } catch (err: any) {
      alert(err.message || 'Failed to remove symbol');
    }
  };

  if (loading) return <div className="loading">Loading watchlist...</div>;

  return (
    <div className="watchlist">
      <h2 className="section-title">Stock Watchlist</h2>
      <p className="section-subtitle">Track custom stocks without owning them. They will be automatically updated in the daily pipeline.</p>
      
      <div className="info-shelf" style={{ margin: '12px 0', padding: '12px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #bae6fd', fontSize: '0.85rem' }}>
         <strong>💡 CSV Required Format:</strong> Just a single column named <code>symbol</code> (e.g., RELIANCE, INFOSYS).
      </div>
      
      <div className="watchlist-controls" style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <form onSubmit={handleAdd} className="watchlist-add-form" style={{ flex: 1, display: 'flex', gap: '8px', position: 'relative' }}>
          <input 
            type="text" 
            placeholder="Type Company or Symbol (e.g. TATA)" 
            value={newSymbol} 
            onChange={e => setNewSymbol(e.target.value)} 
            className="form-input"
            style={{ marginBottom: 0 }}
          />
          {suggestions.length > 0 && (
            <div className="autocomplete-dropdown" style={{ 
                position: 'absolute', top: '100%', left: 0, right: 0, 
                backgroundColor: 'white', border: '1px solid #e2e8f0', 
                borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                zIndex: 1000, marginTop: '4px', maxHeight: '200px', overflowY: 'auto'
            }}>
                {suggestions.map(s => (
                    <div 
                        key={s.symbol} 
                        onClick={() => { setNewSymbol(s.symbol); setSuggestions([]); }}
                        style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid #f1f5f9' }}
                        onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f8fafc'}
                        onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'white'}
                    >
                        <span style={{ fontWeight: 700, color: '#1e293b' }}>{s.symbol}</span>
                        <span style={{ marginLeft: '8px', fontSize: '0.85rem', color: '#64748b' }}>{s.company_name}</span>
                    </div>
                ))}
            </div>
          )}
          <button type="submit" className="btn-primary" style={{ whiteSpace: 'nowrap' }}>Add Stock</button>
        </form>
        
        <div className="csv-upload-btn">
          <input
            type="file"
            id="watchlist-csv"
            accept=".csv"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                setLoading(true);
                const result = await api.uploadWatchlistCsv(file);
                const added = result?.total_processed ?? result?.added ?? '?';
                const msg = result?.message || 'Watchlist updated from CSV';
                alert(`✅ ${msg} (${added} symbols processed)`);
                loadWatchlist();
              } catch (err: any) {
                alert(err.message || 'Upload failed');
              } finally {
                setLoading(false);
                // Reset input so same file can be re-uploaded
                e.target.value = '';
              }
            }}
            style={{ display: 'none' }}
          />
          <label htmlFor="watchlist-csv" className="btn-secondary" style={{ cursor: 'pointer', padding: '10px 16px', display: 'inline-block', borderRadius: '8px' }}>
            📁 Upload CSV
          </label>
        </div>
      </div>
      
      {error && <div className="error-alert">{error}</div>}

      {watchlist.length > 0 ? (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Price</th>
                <th>MRI Grade</th>
                <th>Trend</th>
                <th>Actions</th>
              </tr>
            </thead>
             <tbody>
              {watchlist.map(item => (
                <tr key={item.symbol} style={item.is_pending ? { opacity: 0.6 } : {}} onClick={() => !item.is_pending && onSelectStock(item)} className={item.is_pending ? '' : 'clickable-row'}>
                  <td className="font-bold">{item.symbol}</td>
                  <td>{item.price ? `₹${item.price.toLocaleString()}` : (item.is_pending ? 'Saving...' : 'N/A')}</td>
                  <td>
                    {item.is_pending ? (
                        <span className="badge-pending">💾 Saving...</span>
                    ) : item.is_not_found ? (
                        <span className="action-badge badge-skipped" style={{ background: '#ff4d4f', color: 'white' }}>⚠️ Check Symbol</span>
                    ) : item.score !== null ? (
                      <span className="score-badge">{item.score}/100</span>
                    ) : (
                      <span className="badge-pending">🔄 Tracking...</span>
                    )}
                  </td>

                  <td>
                    {item.is_pending ? '...' : (item.trend_alignment ? (
                      <span className={`action-badge ${item.trend_alignment === 'BULL' ? 'badge-executed' : 'badge-skipped'}`}>
                        {item.trend_alignment}
                      </span>
                    ) : 'N/A')}
                  </td>
                  <td>
                    <button className="btn-danger" onClick={() => handleRemove(item.symbol)} disabled={item.is_pending} style={{ padding: '4px 8px', fontSize: '12px' }}>
                      🗑️ Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">There are no stocks in your watchlist to track here right now. When you add, it will be displayed.</div>
      )}
    </div>
  );
}

/* ─── Main App ────────────────────────────────────────────── */
function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [showAuthPane, setShowAuthPane] = useState(false);
  const [page, setPage] = useState<'dashboard' | 'history' | 'performance' | 'riskaudit' | 'watchlist' | 'admin' | 'shadow'>('dashboard');
  const [selectedStock, setSelectedStock] = useState<any>(null);

  // ... rest of the component
  const urlParams = new URLSearchParams(window.location.search);
  const resetToken = urlParams.get('reset_token');
  const [isResetFlow, setIsResetFlow] = useState(!!resetToken);

  const handleResetComplete = () => {
    // Clear URL without page reload
    window.history.replaceState({}, document.title, window.location.pathname);
    setIsResetFlow(false);
  };

  if (isResetFlow && resetToken) {
    return <ResetPasswordPage token={resetToken} onComplete={handleResetComplete} />;
  }

  if (!authed) {
    if (showAuthPane) {
      return <LoginPage onLogin={() => { setAuthed(true); setShowAuthPane(false); }} onCancel={() => setShowAuthPane(false)} />;
    }
    return <LandingPage onRequestAuth={() => setShowAuthPane(true)} />;
  }

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-icon">📊</span>
          <span className="brand-name">MRI</span>
        </div>
        <div className="nav-links">
          <button className={`nav-link ${page === 'dashboard' ? 'active' : ''}`} onClick={() => setPage('dashboard')}>
            <span className="nav-icon">🏠</span> Dashboard
          </button>
          <button className={`nav-link ${page === 'shadow' ? 'active' : ''}`} onClick={() => setPage('shadow')}>
            <span className="nav-icon">🚀</span> Swing Momentum
          </button>
          <button className={`nav-link ${page === 'history' ? 'active' : ''}`} onClick={() => setPage('history')}>
            <span className="nav-icon">📋</span> History
          </button>
          <button className={`nav-link ${page === 'performance' ? 'active' : ''}`} onClick={() => setPage('performance')}>
            <span className="nav-icon">📈</span> Performance
          </button>
          <button className={`nav-link ${page === 'riskaudit' ? 'active' : ''}`} onClick={() => setPage('riskaudit')}>
            <span className="nav-icon">🛡️</span> Risk Audit
          </button>
          <button className={`nav-link ${page === 'watchlist' ? 'active' : ''}`} onClick={() => setPage('watchlist')}>
            <span className="nav-icon">👀</span> Watchlist
          </button>
          {isAdmin() && (
            <button className={`nav-link ${page === 'admin' ? 'active' : ''}`} onClick={() => setPage('admin')}>
              <span className="nav-icon">🛡️</span> Admin Panel
            </button>
          )}
        </div>
        <div className="sidebar-footer">
          <div className="user-info">{getClientName()}</div>
          <button className="btn-logout" onClick={() => { clearAuth(); setAuthed(false); }}>Logout</button>
        </div>
      </nav>
      <main className="main-content">
        <header className="content-header">
          <h1 className="page-title">
            {page === 'dashboard' ? 'Signal Dashboard' : 
             page === 'shadow' ? 'Swing Momentum' : 
             page === 'history' ? 'Trade History' : 
             page === 'riskaudit' ? 'Portfolio Risk Audit' : 
             page === 'watchlist' ? 'Stock Watchlist' : 
             page === 'admin' ? 'Platform Intelligence' : 'My Performance'}
          </h1>
        </header>
        <div className="content-body">
          {page === 'dashboard' && <DashboardPage onSelectStock={setSelectedStock} />}
          {page === 'shadow' && <ShadowMomentumPage onSelectStock={setSelectedStock} />}
          {page === 'history' && <HistoryPage onSelectStock={setSelectedStock} />}
          {page === 'performance' && <PerformancePage />}
          {page === 'riskaudit' && <RiskAuditPage onSelectStock={setSelectedStock} />}
          {page === 'watchlist' && <WatchlistPage onSelectStock={setSelectedStock} />}
          {page === 'admin' && <AdminDashboard onSelectStock={setSelectedStock} />}
        </div>
      </main>

      {selectedStock && (
        <StockDetailsModal 
          stock={selectedStock} 
          onClose={() => setSelectedStock(null)} 
        />
      )}

      {/* Mobile Bottom Navigation */}
      <nav className="mobile-nav">
        <button className={`mobile-nav-link ${page === 'dashboard' ? 'active' : ''}`} onClick={() => setPage('dashboard')}>
          <span className="nav-icon">🏠</span> Dash
        </button>
        <button className={`mobile-nav-link ${page === 'shadow' ? 'active' : ''}`} onClick={() => setPage('shadow')}>
          <span className="nav-icon">🚀</span> Swing
        </button>
        <button className={`mobile-nav-link ${page === 'riskaudit' ? 'active' : ''}`} onClick={() => setPage('riskaudit')}>
          <span className="nav-icon">🛡️</span> Audit
        </button>

        <button className={`mobile-nav-link ${page === 'watchlist' ? 'active' : ''}`} onClick={() => setPage('watchlist')}>
          <span className="nav-icon">👀</span> Watchlist
        </button>
        <button className={`mobile-nav-link ${page === 'riskaudit' ? 'active' : ''}`} onClick={() => setPage('riskaudit')}>
          <span className="nav-icon">🛡️</span> Audit
        </button>
        <button className={`mobile-nav-link ${page === 'history' ? 'active' : ''}`} onClick={() => setPage('history')}>
          <span className="nav-icon">📋</span> History
        </button>
        {isAdmin() && (
          <button className={`mobile-nav-link ${page === 'admin' ? 'active' : ''}`} onClick={() => setPage('admin')}>
            <span className="nav-icon">🛡️</span> Admin
          </button>
        )}
        <button className="mobile-nav-link" onClick={() => { clearAuth(); setAuthed(false); }}>
          <span className="nav-icon">🚪</span> Logout
        </button>
      </nav>
    </div>
  );
}

export default App;
