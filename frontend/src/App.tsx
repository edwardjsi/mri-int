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
    { label: '1. Trend Integrity (EMA 50 > 200)', value: conditions.ema_50_above_200, weight: '25%' },
    { label: '2. Long-term Bias (200 EMA Slope > 0)', value: conditions.ema_200_slope_positive, weight: '25%' },
    { label: '3. Outperformance (90d RS > 0)', value: conditions.relative_strength, weight: '15%' },
    { label: '4. Alpha-Strength (Near 6m High)', value: conditions.at_6m_high, weight: '15%' },
    { label: '5. Breakout Confirmation (10d High)', value: conditions.breakout_10d, weight: '10%' },
    { label: '6. Liquidity Gate (Volume Surge)', value: conditions.volume_surge, weight: '5%' },
    { label: '7. Price Quality (Day Range %)', value: conditions.price_quality, weight: '5%' },
  ];

  const isGoldenSetup = score === 100;

  return (
    <div className="score-breakdown">
      <div className="summary-stat" style={{ marginBottom: '1rem', textAlign: 'center' }}>
        <span className="summary-label">Total MRI Score</span>
        <div className="stat-value" style={{ fontSize: '2rem', color: isGoldenSetup ? '#22c55e' : '#60a5fa' }}>
          {score}/100 {isGoldenSetup && '🚀'}
        </div>
        {isGoldenSetup && <div style={{ fontSize: '12px', color: '#22c55e', fontWeight: 'bold' }}>THE GOLDEN SETUP</div>}
      </div>
      <div className="conditions-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {items.map((item, idx) => (
          <div key={idx} className="condition-item" style={{ padding: '8px', border: '1px solid #334155', borderRadius: '4px' }}>
            <div className="condition-label" style={{ fontSize: '11px' }}>
              {item.label}
              <div style={{ fontSize: '9px', color: '#64748b' }}>Weight: {item.weight}</div>
            </div>
            <div className={`condition-value ${item.value ? 'condition-pass' : 'condition-fail'}`} style={{ fontSize: '10px', marginTop: '4px' }}>
              {item.value ? '✅ PASS' : '❌ FAIL'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Quality Verdict Component (Fundamentals) ─── */
function QualityVerdict({ symbol }: { symbol: string }) {
  const [verdict, setVerdict] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getQualityVerdict(symbol)
      .then(setVerdict)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) return <div style={{ fontSize: '12px', color: '#64748b', textAlign: 'center', padding: '10px' }}>Analyzing business quality...</div>;
  if (!verdict) return null;

  const categoryColors: any = {
    'HIGH_QUALITY': '#22c55e',
    'EARLY_COMPOUNDER': '#a855f7',
    'WATCHLIST': '#eab308',
    'REJECT': '#ef4444'
  };

  const scores = [
    { label: 'Revenue', val: verdict.revenue_score },
    { label: 'Margins', val: verdict.margin_score },
    { label: 'Leverage', val: verdict.leverage_score },
    { label: 'Working Cap', val: verdict.wc_score },
    { label: 'ROCE/WACC', val: verdict.roce_score },
    { label: 'Evolution', val: verdict.evolution_score },
  ];

  return (
    <div className="quality-verdict" style={{ marginTop: '1.5rem', padding: '12px', border: '1px solid #334155', borderRadius: '8px', background: '#0f172a' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 'bold', textTransform: 'uppercase' }}>Fundamental Quality Analysis</span>
          {verdict.velocity !== undefined && (
            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
              <span style={{ fontSize: '10px', color: verdict.score_change >= 0 ? '#22c55e' : '#ef4444' }}>
                Change: {verdict.score_change >= 0 ? '+' : ''}{verdict.score_change?.toFixed(1)}
              </span>
              <span style={{ fontSize: '10px', color: verdict.velocity >= 2 ? '#a855f7' : '#94a3b8' }}>
                Velocity: {verdict.velocity?.toFixed(2)}
              </span>
            </div>
          )}
        </div>
        <span style={{
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 'bold',
          background: (categoryColors[verdict.category] || '#475569') + '20',
          color: categoryColors[verdict.category] || '#94a3b8',
          border: `1px solid ${categoryColors[verdict.category]}40`
        }}>
          {verdict.category}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px' }}>
        {scores.map(s => (
          <div key={s.label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '9px', color: '#64748b' }}>{s.label}</div>
            <div style={{ fontSize: '12px', fontWeight: 'bold', color: s.val >= 7 ? '#22c55e' : (s.val >= 5 ? '#eab308' : '#ef4444') }}>
              {s.val}/10
            </div>
          </div>
        ))}
      </div>

      {verdict.qil_flags && verdict.qil_flags.length > 0 && (
        <div style={{ marginTop: '8px', borderTop: '1px solid #1e293b', paddingTop: '8px' }}>
          <div style={{ fontSize: '9px', color: '#64748b', marginBottom: '4px', textTransform: 'uppercase' }}>Qualitative Intelligence (QIL) Signals</div>
          {verdict.qil_flags.map((f: string, i: number) => (
            <div key={i} style={{ fontSize: '10px', color: '#60a5fa', marginBottom: '2px' }}>• {f}</div>
          ))}
        </div>
      )}

      {verdict.flags && verdict.flags.length > 0 && (
        <div style={{ marginTop: '8px' }}>
          {verdict.flags.map((f: string, i: number) => (
            <div key={i} style={{ fontSize: '10px', color: f.includes('🚨') ? '#ef4444' : '#eab308', marginBottom: '2px' }}>{f}</div>
          ))}
        </div>
      )}

      <div style={{ marginTop: '10px', fontSize: '11px', color: '#94a3b8', fontStyle: 'italic', lineHeight: '1.4', borderTop: '1px solid #1e293b', paddingTop: '8px' }}>
        "Quality investor framework: {verdict.score?.toFixed(0)}% aligned with structural compounder logic."
      </div>
    </div>
  );
}

/* ─── Stock Details Modal ────────────────────────────────── */
function StockDetailsModal({ stock, onClose }: { stock: any, onClose: () => void }) {
  const [debating, setDebating] = useState(false);
  const [debateStatus, setDebateStatus] = useState<string | null>(null);

  const handleTriggerDebate = async () => {
    if (!confirm(`Trigger AI Forensic Debate for ${stock.symbol}? This will analyze guidance vs reality and email you a deep-dive report.`)) return;
    setDebating(true);
    setDebateStatus(null);
    try {
      const res = await api.triggerDebate(stock.symbol);
      setDebateStatus(res.message || "Debate triggered! Check your email in a few minutes.");
    } catch (err: any) {
      setDebateStatus("Failed to start debate. Ensure this stock has fundamental data.");
      console.error(err);
    } finally {
      setDebating(false);
    }
  };

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

        <QualityVerdict symbol={stock.symbol} />

        {debateStatus && (
          <div style={{
            marginTop: '1.5rem',
            padding: '12px',
            borderRadius: '8px',
            background: debateStatus.includes('Failed') ? '#ef444415' : '#22c55e15',
            border: `1px solid ${debateStatus.includes('Failed') ? '#ef444440' : '#22c55e40'}`,
            color: debateStatus.includes('Failed') ? '#fca5a5' : '#86efac',
            fontSize: '12px',
            textAlign: 'center'
          }}>
            {debateStatus}
          </div>
        )}

        <div className="modal-actions" style={{ marginTop: '1.5rem', display: 'flex', gap: '10px' }}>
          <button
            className="btn-secondary"
            onClick={handleTriggerDebate}
            disabled={debating}
            style={{
              flex: 1,
              background: 'linear-gradient(135deg, #6d28d9 0%, #4c1d95 100%)',
              color: 'white',
              border: 'none',
              fontWeight: 'bold'
            }}
          >
            {debating ? '🧠 AI Debating...' : '📊 AI Forensic Debate'}
          </button>
          <button className="btn-primary" onClick={onClose} style={{ flex: 1 }}>Close Report</button>
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

function LandingPage({ onRequestAuth }: { onRequestAuth: () => void }) {
  return (
    <div className="landing-shell" style={{ maxWidth: '900px', margin: '0 auto', padding: '40px 20px', lineHeight: '1.6' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '60px' }}>
        <h1 style={{ fontSize: '2.8rem', marginBottom: '20px', color: '#ffffff' }}>
          The Market Regime Discovery That Changes Everything
        </h1>
        <p style={{ fontSize: '1.2rem', color: '#94a3b8', fontStyle: 'italic' }}>
          Dear Professional Investor,
        </p>
      </div>

      {/* Main Content */}
      <div style={{ fontSize: '1.1rem', color: '#e2e8f0', marginBottom: '40px' }}>
        <p style={{ marginBottom: '24px' }}>
          Most investment systems fail for a simple reason: they treat all market conditions as identical.
        </p>
        <p style={{ marginBottom: '24px' }}>
          Whether the Nifty is grinding higher in a risk-on environment, churning sideways in consolidation, or falling in a risk-off phase, traditional analysis applies the same fundamental and technical criteria. Same screening parameters. Same selection logic. Same position sizing approach.
        </p>
        <p style={{ marginBottom: '24px', fontWeight: 'bold', color: '#f59e0b' }}>
          This is mathematically flawed.
        </p>
        <p style={{ marginBottom: '40px' }}>
          Markets operate in distinct, measurable regimes. And after years of development and backtesting, we've created a system that identifies these regimes with documented accuracy—then adapts every aspect of stock selection accordingly.
        </p>

        {/* The Backtested Foundation */}
        <h2 style={{ fontSize: '1.8rem', color: '#60a5fa', marginBottom: '20px', marginTop: '50px' }}>
          The Backtested Foundation
        </h2>
        <p style={{ marginBottom: '24px' }}>
          The Market Regime Intelligence Platform v2.0 represents a breakthrough in systematic investing for Indian equities. Over multiple market cycles, our regime identification system has demonstrated the ability to classify market conditions into three primary states: Risk-On, Risk-Off, and Neutral.
        </p>
        <p style={{ marginBottom: '24px' }}>
          The backtested results speak clearly:
        </p>
        <p style={{ marginBottom: '24px' }}>
          During Risk-On periods, our system identifies momentum-driven opportunities with technical strength indicators that historically outperformed the Nifty. During Risk-Off phases, it shifts focus to quality defensive stocks with superior fundamental metrics. In Neutral regimes, it balances both approaches while managing position sizes more conservatively.
        </p>

        <div style={{ background: '#1e293b', padding: '24px', borderRadius: '12px', border: '1px solid #334155', marginBottom: '30px' }}>
          <p style={{ fontWeight: 'bold', color: '#22c55e', marginBottom: '16px' }}>
            What this means for your investment results:
          </p>
          <p style={{ marginBottom: '16px' }}>
            Portfolio drawdowns typically reduce by 15-25% during market downturns when regime intelligence guides position sizing and stock selection. Alpha generation improves during trending markets because the system identifies and acts on regime-appropriate opportunities rather than fighting market character.
          </p>
        </div>

        {/* The Systematic Implementation */}
        <h2 style={{ fontSize: '1.8rem', color: '#60a5fa', marginBottom: '20px', marginTop: '50px' }}>
          The Systematic Implementation
        </h2>
        <p style={{ marginBottom: '24px' }}>
          Our backtested Market Regime Intelligence drives a comprehensive 7-step stock selection system:
        </p>

        <div style={{ marginBottom: '30px' }}>
          <h3 style={{ color: '#a78bfa', marginBottom: '12px' }}>Step 1-3: Technical Foundation</h3>
          <ul style={{ paddingLeft: '20px', marginBottom: '20px' }}>
            <li>Momentum scoring adjusted for current market regime</li>
            <li>Volume and price action analysis weighted by regime context</li>
            <li>Support/resistance levels interpreted through regime lens</li>
          </ul>

          <h3 style={{ color: '#a78bfa', marginBottom: '12px' }}>Step 4-5: Fundamental Quality</h3>
          <ul style={{ paddingLeft: '20px', marginBottom: '20px' }}>
            <li>Quality Investor Framework (QIF) scoring across seven business dimensions</li>
            <li>Financial health metrics prioritized by regime requirements</li>
            <li>Management quality and competitive positioning analysis</li>
          </ul>

          <h3 style={{ color: '#a78bfa', marginBottom: '12px' }}>Step 6-7: Integration and Validation</h3>
          <ul style={{ paddingLeft: '20px', marginBottom: '20px' }}>
            <li>Regime-selection alignment verification</li>
            <li>Position sizing recommendations based on market character</li>
            <li>AI Forensic Debate Engine cross-validation</li>
          </ul>
        </div>

        <p style={{ marginBottom: '40px' }}>
          Each evening after market hours, you receive the current regime classification alongside 3-5 stock recommendations that leverage this intelligence. The system screens the entire Nifty 500 universe, applying regime-appropriate criteria to identify opportunities that align with current market character.
        </p>

        {/* Professional Validation */}
        <h2 style={{ fontSize: '1.8rem', color: '#60a5fa', marginBottom: '20px', marginTop: '50px' }}>
          Professional Validation
        </h2>
        <p style={{ marginBottom: '24px' }}>
          The MRI Platform operates under institutional standards:
        </p>
        <ul style={{ paddingLeft: '20px', marginBottom: '30px' }}>
          <li style={{ marginBottom: '8px' }}>All backtested performance claims are documented with detailed methodology</li>
          <li style={{ marginBottom: '8px' }}>Risk management protocols include maximum position sizes and stop-loss parameters</li>
          <li style={{ marginBottom: '8px' }}>Performance attribution clearly separates regime timing benefits from stock selection alpha</li>
          <li style={{ marginBottom: '8px' }}>System includes built-in performance tracking against Nifty benchmarks</li>
        </ul>

        {/* Why This Matters Now */}
        <h2 style={{ fontSize: '1.8rem', color: '#60a5fa', marginBottom: '20px', marginTop: '50px' }}>
          Why This Matters Now
        </h2>
        <p style={{ marginBottom: '24px' }}>
          Indian equity markets have entered a phase where regime awareness becomes crucial. Global liquidity conditions, domestic policy cycles, and sectoral rotation patterns create distinct market characters that demand adaptive investment approaches.
        </p>
        <p style={{ marginBottom: '40px' }}>
          The MRI Platform doesn't replace your existing investment process—it enhances decision-making with regime context that improves timing, selection, and risk management simultaneously.
        </p>

        {/* Your Next Step - Pricing & CTA */}
        <div style={{ background: '#1e293b', padding: '40px', borderRadius: '16px', border: '2px solid #60a5fa', textAlign: 'center', marginTop: '50px' }}>
          <h2 style={{ fontSize: '1.8rem', color: '#60a5fa', marginBottom: '20px' }}>
            Your Next Step
          </h2>
          <p style={{ marginBottom: '24px' }}>
            We're offering qualified professional investors the opportunity to experience the backtested advantage firsthand.
          </p>

          <div style={{ marginBottom: '30px', textAlign: 'left' }}>
            <h3 style={{ color: '#22c55e', marginBottom: '16px' }}>The trial subscription includes:</h3>
            <ul style={{ paddingLeft: '20px' }}>
              <li>30 days of daily regime intelligence and stock recommendations</li>
              <li>Complete access to the 7-step selection methodology</li>
              <li>Historical performance data and backtesting documentation</li>
              <li>Direct access to system developers for technical questions</li>
              <li>Performance tracking tools to measure regime-awareness benefits</li>
            </ul>
          </div>

          <div style={{ marginBottom: '30px' }}>
            <p style={{ fontSize: '1.2rem', color: '#f59e0b', fontWeight: 'bold', marginBottom: '8px' }}>
              Investment: ₹12,000 per month (₹1,44,000 annually)
            </p>
            <p style={{ fontSize: '1.1rem', color: '#22c55e', fontWeight: 'bold' }}>
              Professional trial: First 30 days at ₹3,000 to evaluate system effectiveness
            </p>
          </div>

          <div style={{ marginBottom: '40px', padding: '20px', background: '#0f172a', borderRadius: '8px' }}>
            <p style={{ fontWeight: 'bold', color: '#22c55e', marginBottom: '8px' }}>
              Clear success criteria:
            </p>
            <p style={{ fontSize: '0.95rem' }}>
              If the MRI Platform doesn't demonstrate measurable improvement in your risk-adjusted returns within the trial period, we'll provide a complete refund along with detailed performance attribution analysis.
            </p>
          </div>

          <button
            className="btn-primary"
            onClick={onRequestAuth}
            style={{
              fontSize: '1.2rem',
              padding: '16px 32px',
              marginBottom: '20px',
              background: '#22c55e',
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Start MRI Trial → Access Platform
          </button>

          <p style={{ fontSize: '0.9rem', color: '#94a3b8', marginTop: '16px' }}>
            Click above to access the platform and begin your professional trial
          </p>
        </div>

        {/* Signature */}
        <div style={{ marginTop: '60px', paddingTop: '30px', borderTop: '1px solid #334155' }}>
          <p style={{ marginBottom: '8px' }}>Respectfully,</p>
          <p style={{ fontWeight: 'bold', color: '#60a5fa', marginBottom: '4px' }}>Immanuel Santosh</p>
          <p style={{ fontSize: '0.95rem', color: '#94a3b8' }}>Lead Developer, MRI Platform & Investor</p>
        </div>

        {/* Disclaimer */}
        <div style={{ marginTop: '40px', padding: '20px', background: '#1e293b', borderRadius: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>
          <p style={{ fontStyle: 'italic' }}>
            <strong>Disclaimer:</strong> Past performance doesn't guarantee future results. The MRI Platform provides decision-support analytics for professional investors. All investment decisions remain your responsibility. Please review complete terms and risk disclosures before subscribing.
          </p>
        </div>
      </div>
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
  const colorMap: Record<string, string> = { BULLISH: '#22c55e', BEARISH: '#ef4444', SIDEWAYS: '#eab308', NEUTRAL: '#6b7280' };
  const emojiMap: Record<string, string> = { BULLISH: '🟢', BEARISH: '🔴', SIDEWAYS: '🟡', NEUTRAL: '⚪' };
  const color = colorMap[regime?.regime] || '#6b7280';
  return (
    <div className="card regime-card" style={{ borderLeftColor: color }}>
      <div className="card-label">Market Regime</div>
      <div className="regime-value" style={{ color }}>
        {emojiMap[regime?.regime] || '⚪'} {regime?.regime || 'Loading...'}
      </div>
      <div className="card-meta">
        {regime?.date && <>As of {regime.date} · EMA 200: ₹{regime.ema_200?.toLocaleString()}</>}
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
  const isGoldenSetup = signal.score === 100;
  const isBreakout = !!signal.conditions?.breakout_10d;

  return (
    <>
      <div
        className={`signal-card ${isBuy ? 'signal-buy' : 'signal-sell'} clickable-row`}
        onClick={() => onSelectStock(signal)}
      >
        <div className="signal-header">
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="signal-symbol">{signal.symbol}</span>
            {isGoldenSetup && <span className="score-trend-indicator" style={{ fontSize: '9px', marginTop: '2px' }}>🚀 GOLDEN SETUP</span>}
            {isBreakout && !isGoldenSetup && <span className="score-trend-indicator" style={{ fontSize: '9px', marginTop: '2px', color: '#60a5fa' }}>✨ BREAKOUT</span>}
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
              className={`signal-card ${s.is_breakout ? 'signal-buy' : ''} clickable-row`}
              style={{ borderLeftWidth: s.is_breakout ? '4px' : '1px', borderLeftColor: s.is_breakout ? '#22c55e' : '#334155' }}
              onClick={() => onSelectStock(stockWithConditions)}
            >
              <div className="signal-header">
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span className="signal-symbol">{s.symbol}</span>
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

/* ─── Dashboard Page ─────────────────────────────────────── */
function DashboardPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [regime, setRegime] = useState<any>(null);
  const [signals, setSignals] = useState<any>(null);
  const [pending, setPending] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [positions, setPositions] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [qualityImprovers, setQualityImprovers] = useState<any[]>([]);
  const [trajectoryAlerts, setTrajectoryAlerts] = useState<any[]>([]);
  const [showAddCapital, setShowAddCapital] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [r, s, p, sum, prof, pos, improvers, alerts] = await Promise.all([
        api.getRegime(),
        api.getTodaySignals().catch(() => ({ signals: [] })),
        api.getPendingSignals().catch(() => []),
        api.getDailySummary().catch(() => null),
        api.getProfile().catch(() => null),
        api.getPositions().catch(() => ({ positions: [] })),
        api.getTopImprovers(6).catch(() => []),
        api.getTrajectoryAlerts().catch(() => []),
      ]);
      setRegime(r);
      setSignals(s);
      setPending(p);
      setSummary(sum);
      setProfile(prof);
      setPositions(pos);
      setQualityImprovers(improvers);
      setTrajectoryAlerts(alerts);
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

  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortIcon = (key: string) => {
    if (!sortConfig || sortConfig.key !== key) return ' ↕️';
    return sortConfig.direction === 'asc' ? ' 🔼' : ' 🔽';
  };

  const sortedPositions = useMemo(() => {
    if (!positions?.positions) return [];
    let sortableItems = [...positions.positions];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        let aVal = a[sortConfig.key];
        let bVal = b[sortConfig.key];
        
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
  }, [positions?.positions, sortConfig]);

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

      <section className="section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: '16px', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <div>
            <h2 className="section-title" style={{ margin: 0 }}>💎 Quality Intelligence</h2>
            <p className="section-subtitle" style={{ marginTop: '6px' }}>
              The latest QIF and trajectory layer is now surfaced directly on the main dashboard.
            </p>
          </div>
          {trajectoryAlerts.length > 0 && (
            <div style={{ fontSize: '12px', color: '#cbd5e1', background: 'rgba(168, 85, 247, 0.12)', border: '1px solid rgba(168, 85, 247, 0.35)', borderRadius: '999px', padding: '8px 12px' }}>
              {trajectoryAlerts.length} live trajectory alert{trajectoryAlerts.length === 1 ? '' : 's'}
            </div>
          )}
        </div>

        {qualityImprovers.length > 0 ? (
          <div className="signals-grid">
            {qualityImprovers.map((stock: any) => (
              <div
                key={`quality-${stock.symbol}`}
                className="signal-card clickable-row"
                style={{ borderLeft: '4px solid #a855f7' }}
                onClick={() => onSelectStock({ ...stock, symbol: stock.symbol })}
              >
                <div className="signal-header">
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span className="signal-symbol">{stock.symbol}</span>
                    <span className="score-trend-indicator" style={{ fontSize: '10px', marginTop: '2px', color: '#c084fc', fontWeight: 800 }}>
                      {stock.score_change > 5 ? '🚀 BREAKOUT CANDIDATE' : '📈 QUALITY IMPROVER'}
                    </span>
                  </div>
                  <span className="score-badge" style={{ fontSize: '13px', padding: '4px 10px' }}>
                    {parseFloat(stock.score || 0).toFixed(0)}
                  </span>
                </div>
                <div className="signal-details">
                  <div className="signal-detail">
                    <span className="detail-label">Change</span>
                    <span className="detail-value" style={{ color: stock.score_change >= 0 ? '#22c55e' : '#ef4444' }}>
                      {stock.score_change >= 0 ? '+' : ''}{parseFloat(stock.score_change || 0).toFixed(1)}
                    </span>
                  </div>
                  <div className="signal-detail">
                    <span className="detail-label">Velocity</span>
                    <span className="detail-value" style={{ color: '#c084fc' }}>
                      {parseFloat(stock.velocity || 0).toFixed(2)}
                    </span>
                  </div>
                </div>
                <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11px', color: '#94a3b8' }}>Verdict</span>
                  <span style={{
                    padding: '3px 8px',
                    borderRadius: '999px',
                    fontSize: '10px',
                    fontWeight: 700,
                    background: 'rgba(168, 85, 247, 0.12)',
                    border: '1px solid rgba(168, 85, 247, 0.35)',
                    color: '#e9d5ff'
                  }}>
                    {stock.category || 'WATCHLIST'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state" style={{ marginTop: '8px' }}>
            The new Quality Intelligence layer is live, but the QIF improver feed is still empty. Once Step 7/backfill data lands in `quality_verdicts`, the newest dashboard cards will populate here.
          </div>
        )}

        {trajectoryAlerts.length > 0 && (
          <div style={{ marginTop: '16px', display: 'grid', gap: '10px' }}>
            {trajectoryAlerts.slice(0, 4).map((alert: any, idx: number) => (
              <div
                key={`trajectory-alert-${alert.symbol || idx}`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: '12px',
                  alignItems: 'center',
                  background: 'rgba(15, 23, 42, 0.65)',
                  border: '1px solid rgba(148, 163, 184, 0.18)',
                  borderRadius: '12px',
                  padding: '12px 14px'
                }}
              >
                <div>
                  <div style={{ color: '#f8fafc', fontWeight: 700, fontSize: '14px' }}>
                    {alert.symbol} {alert.signal ? `• ${alert.signal}` : ''}
                  </div>
                  <div style={{ color: '#94a3b8', fontSize: '12px', marginTop: '3px' }}>
                    Score {parseFloat(alert.score || 0).toFixed(1)} | Change {parseFloat(alert.score_change || 0).toFixed(1)} | Velocity {parseFloat(alert.velocity || 0).toFixed(2)}
                  </div>
                </div>
                <button
                  className="btn-secondary"
                  style={{ width: 'auto', margin: 0, padding: '8px 12px', fontSize: '12px' }}
                  onClick={() => onSelectStock({ ...alert, symbol: alert.symbol })}
                >
                  Inspect
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── My Positions ── */}
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
                <tr>
                  <th onClick={() => handleSort('symbol')} style={{ cursor: 'pointer' }}>Symbol {getSortIcon('symbol')}</th>
                  <th>Source</th>
                  <th onClick={() => handleSort('current_price')} style={{ cursor: 'pointer' }}>Price {getSortIcon('current_price')}</th>
                  <th>Qty</th>
                  <th>Value</th>
                  <th onClick={() => handleSort('pnl_pct')} style={{ cursor: 'pointer' }}>P&L % {getSortIcon('pnl_pct')}</th>
                </tr>
              </thead>
              <tbody>
                {sortedPositions.map((p: any) => (
                  <tr key={`${p.source}-${p.symbol}`} onClick={() => onSelectStock(p)} className="clickable-row">
                    <td className="font-bold">
                      {p.breakout_candidate && (
                        <span title="Breakout candidate today" style={{ marginRight: '4px' }}>🚀</span>
                      )}
                      {p.symbol}
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

      {/* ── Signals ── */}
      <section className="section">
        <h2 className="section-title">✨ MRI Signals (Daily Alignment)</h2>
        {todaySignals.length > 0 ? (
          <div className="signals-grid">
            {todaySignals.map((s: any) => (
              <SignalCard key={s.id} signal={s} totalCapital={totalCapital} onAction={handleAction} onSelectStock={onSelectStock} />
            ))}
          </div>
        ) : (
          <div className="empty-state">No new daily signals today. System is standing down.</div>
        )}
      </section>

      {pendingOlder.length > 0 && (
        <section className="section">
          <h2 className="section-title">⏳ Open/Pending Signals</h2>
          <div className="signals-grid">
            {pendingOlder.map((s: any) => (
              <SignalCard key={s.id} signal={s} totalCapital={totalCapital} onAction={handleAction} onSelectStock={onSelectStock} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/* ─── History Page ────────────────────────────────────────── */
function HistoryPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getActionHistory()
      .then(setHistory)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Retrieving history...</div>;

  return (
    <div className="history">
      <h2 className="section-title">📜 Action History</h2>
      {history.length > 0 ? (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr><th>Date</th><th>Symbol</th><th>Action</th><th>Price</th><th>Qty</th><th>Status</th></tr>
            </thead>
            <tbody>
              {history.map((a: any, idx: number) => (
                <tr key={idx} onClick={() => onSelectStock(a)} className="clickable-row">
                  <td>{a.recorded_at ? new Date(a.recorded_at).toLocaleDateString() : (a.date || 'N/A')}</td>
                  <td className="font-bold">{a.symbol}</td>
                  <td><span className={`action-badge ${a.action === 'EXECUTED' ? 'badge-executed' : 'badge-skipped'}`}>{a.action}</span></td>
                  <td>₹{a.actual_price?.toLocaleString()}</td>
                  <td>{a.quantity}</td>
                  <td>{a.regime}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">No recorded actions found.</div>
      )}
    </div>
  );
}

/* ─── Performance Page ────────────────────────────────────── */
function PerformancePage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getPerformance()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Calculating performance metrics...</div>;
  if (!data) return <div className="empty-state">Performance data currently unavailable.</div>;

  return (
    <div className="performance">
      <div className="dashboard-top-row">
        <div className="card performance-card">
          <div className="card-label">Strategy CAGR</div>
          <div className="performance-value" style={{ color: data.cagr >= 0 ? '#22c55e' : '#ef4444' }}>
            {data.cagr >= 0 ? '+' : ''}{data.cagr}%
          </div>
          <div className="card-meta">Benchmark: {data.benchmark_cagr}%</div>
        </div>
        <div className="card performance-card">
          <div className="card-label">Max Drawdown</div>
          <div className="performance-value" style={{ color: '#ef4444' }}>{data.max_drawdown}%</div>
          <div className="card-meta">Benchmark: {data.benchmark_drawdown}%</div>
        </div>
        <div className="card performance-card">
          <div className="card-label">Sharpe Ratio</div>
          <div className="performance-value" style={{ color: data.sharpe >= 1 ? '#22c55e' : '#eab308' }}>
            {data.sharpe}
          </div>
          <div className="card-meta">Risk-adjusted return</div>
        </div>
      </div>

      <section className="section" style={{ height: '400px', marginTop: '2rem' }}>
        <h3 className="section-title">Equity Curve</h3>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.equity_curve}>
            <XAxis dataKey="date" hide />
            <YAxis hide domain={['auto', 'auto']} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="strategy" stroke="#3b82f6" dot={false} strokeWidth={2} name="MRI Strategy" />
            <Line type="monotone" dataKey="benchmark" stroke="#94a3b8" dot={false} strokeWidth={2} name="Nifty 50" />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

/* ─── Risk Audit Page ─────────────────────────────────────── */
function RiskAuditPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [results, setRiskResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<any>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isRegrading, setIsRegrading] = useState(false);

  const loadStatus = async () => {
    try {
      const res = await api.getHoldingsStatus();
      setStatus(res);
    } catch (err) { console.error(err); }
  };

  useEffect(() => { loadStatus(); }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const res = await api.uploadHoldings(file);
      setRiskResults(res);
      await loadStatus();
      alert(`Portfolio uploaded and analysed!`);
    } catch (err: any) { alert(err.message); }
    finally { setUploading(false); }
  };

  const handleDeleteAll = async () => {
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      window.setTimeout(() => setShowDeleteConfirm(false), 8000);
      return;
    }
    try {
      await api.deleteAllHoldings();
      setRiskResults(null);
      await loadStatus();
      setShowDeleteConfirm(false);
      alert("Holdings deleted.");
    } catch (err: any) { alert(err.message); }
  };

  const handleRegrade = async () => {
    const doEmail = confirm("Email you the updated Risk Audit report after regrading?");
    setIsRegrading(true);
    try {
      const res = await api.regradeHoldingsSync(doEmail);
      setRiskResults(res);
      await loadStatus();
      alert(`Regrade complete. ${doEmail ? "Email sent." : ""}`);
    } catch (err: any) { alert(err.message); }
    finally { setIsRegrading(false); }
  };

  return (
    <div className="risk-audit">
      <section className="panel-card" style={{ marginBottom: '2rem' }}>
        <h2 className="section-title">🛡️ Digital Twin Portfolio Audit</h2>
        <p className="card-meta">Upload your Zerodha/External holdings CSV to analyze quality and regime alignment.</p>
        
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} className="form-input" style={{ width: 'auto' }} />
          <button className="btn-primary" onClick={handleUpload} disabled={!file || uploading}>
            {uploading ? 'Analyzing...' : 'Upload & Audit'}
          </button>
          {status?.holdings_count > 0 && (
            <>
              <button className="btn-secondary" onClick={handleRegrade} disabled={isRegrading}>
                {isRegrading ? 'Regrading...' : '🔄 Regrade Sync'}
              </button>
              <button className="btn-danger" onClick={handleDeleteAll} style={{ opacity: showDeleteConfirm ? 1 : 0.6 }}>
                {showDeleteConfirm ? '⚠️ Click to Confirm Delete' : '🗑️ Clear Digital Twin'}
              </button>
            </>
          )}
        </div>
        {status && (
          <div style={{ marginTop: '1rem', fontSize: '13px', color: '#94a3b8' }}>
            Current Twin: <b>{status.holdings_count} symbols</b> | Last Audit: {status.last_audit ? new Date(status.last_audit).toLocaleString() : 'Never'}
          </div>
        )}
      </section>

      {results && (
        <section className="panel-card">
          <h3 className="section-title">Audit Results</h3>
          <div className="summary-stats" style={{ marginBottom: '2rem' }}>
             <div className="summary-stat">
               <span className="summary-label">Audit Grade</span>
               <span className="summary-value" style={{ color: '#22c55e' }}>{results.overall_grade}</span>
             </div>
             <div className="summary-stat">
               <span className="summary-label">Regime Alignment</span>
               <span className="summary-value">{results.regime_alignment_score}/100</span>
             </div>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead><tr><th>Symbol</th><th>Qty</th><th>MRI Score</th><th>Setup</th><th>Verdict</th></tr></thead>
              <tbody>
                {results.results.map((r: any) => (
                  <tr key={r.symbol} onClick={() => onSelectStock(r)} className="clickable-row">
                    <td className="font-bold">{r.symbol}</td>
                    <td>{r.quantity}</td>
                    <td><span className="score-badge">{r.total_score}/100</span></td>
                    <td>{r.setup_grade}</td>
                    <td>{r.quality_category || 'N/A'}</td>
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

/* ─── Watchlist Page ─────────────────────────────────────── */
function WatchlistPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSymbol, setNewSymbol] = useState('');
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortIcon = (key: string) => {
    if (!sortConfig || sortConfig.key !== key) return ' ↕️';
    return sortConfig.direction === 'asc' ? ' 🔼' : ' 🔽';
  };

  const sortedWatchlist = useMemo(() => {
    let sortableItems = [...watchlist];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        let aVal = a[sortConfig.key];
        let bVal = b[sortConfig.key];
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
  }, [watchlist, sortConfig]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (newSymbol.length >= 2) {
        try {
          const results = await api.searchStocks(newSymbol);
          setSuggestions(results || []);
        } catch (e) { setSuggestions([]); }
      } else { setSuggestions([]); }
    }, 300);
    return () => clearTimeout(timer);
  }, [newSymbol]);

  const loadWatchlist = async () => {
    try {
      const data = await api.getWatchlist();
      setWatchlist(data);
    } catch (err: any) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadWatchlist(); }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) return;
    setError('');
    const optimisticItem = { symbol, price: null, score: null, trend_alignment: null, is_pending: true };
    setWatchlist(prev => [optimisticItem, ...prev]);
    setNewSymbol('');
    setSuggestions([]);
    try {
      await api.addToWatchlist(symbol);
      loadWatchlist();
    } catch (err: any) {
      setError(err.message || 'Failed to add symbol');
      setWatchlist(prev => prev.filter(item => item.symbol !== symbol));
    }
  };

  const handleRemove = async (symbol: string) => {
    if (!confirm(`Remove ${symbol} from watchlist?`)) return;
    try {
      await api.removeFromWatchlist(symbol);
      loadWatchlist();
    } catch (err: any) { alert(err.message); }
  };

  if (loading) return <div className="loading">Loading your watchlist...</div>;

  return (
    <div className="watchlist">
      <section className="panel-card" style={{ marginBottom: '2rem' }}>
        <h2 className="section-title">👀 Market Watchlist</h2>
        <p className="card-meta">Track specific symbols for regime alignment and score triggers.</p>
        
        <form onSubmit={handleAdd} style={{ marginTop: '1.5rem', display: 'flex', gap: '10px', position: 'relative' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              placeholder="Enter symbol (e.g. RELIANCE)"
              value={newSymbol}
              onChange={e => setNewSymbol(e.target.value.toUpperCase())}
              className="form-input"
              style={{ width: '100%' }}
            />
            {suggestions.length > 0 && (
              <div className="autocomplete-dropdown">
                {suggestions.map((s, i) => (
                  <div key={i} className="suggestion-item" onClick={() => { setNewSymbol(s.symbol); setSuggestions([]); }}>
                    <b>{s.symbol}</b> - {s.company_name}
                  </div>
                ))}
              </div>
            )}
          </div>
          <button type="submit" className="btn-primary" style={{ width: 'auto', padding: '0 24px' }}>Add to List</button>
        </form>
        {error && <div style={{ color: '#ef4444', fontSize: '12px', marginTop: '8px' }}>{error}</div>}
      </section>

      {watchlist.length > 0 ? (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('symbol')} style={{ cursor: 'pointer' }}>Symbol {getSortIcon('symbol')}</th>
                <th onClick={() => handleSort('price')} style={{ cursor: 'pointer' }}>Price {getSortIcon('price')}</th>
                <th onClick={() => handleSort('score')} style={{ cursor: 'pointer' }}>MRI Grade {getSortIcon('score')}</th>
                <th onClick={() => handleSort('perx_score')} style={{ cursor: 'pointer' }}>PERX {getSortIcon('perx_score')}</th>
                <th onClick={() => handleSort('trend_alignment')} style={{ cursor: 'pointer' }}>Trend {getSortIcon('trend_alignment')}</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sortedWatchlist.map((item: any) => (
                <tr key={item.symbol} className={item.is_pending ? 'row-pending' : 'clickable-row'} onClick={() => !item.is_pending && onSelectStock(item)}>
                  <td className="font-bold">
                    {item.breakout_candidate && (
                      <span title="Breakout candidate today" style={{ marginRight: '4px' }}>🚀</span>
                    )}
                    {item.symbol}
                  </td>
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
                    {item.is_pending ? '...' : (item.perx_score !== undefined && item.perx_score !== null ? (
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span className="score-badge" style={{ background: '#2563eb' }}>{item.perx_score}</span>
                        <span style={{ fontSize: '9px', color: '#94a3b8', marginTop: '2px' }}>{item.perx_lifecycle}</span>
                      </div>
                    ) : 'N/A')}
                  </td>
                  <td>
                    {item.is_pending ? '...' : (item.trend_alignment ? (
                      <span className={`action-badge ${item.trend_alignment === 'BULL' ? 'badge-executed' : 'badge-skipped'}`}>
                        {item.trend_alignment}
                      </span>
                    ) : 'N/A')}
                  </td>
                  <td>
                    <button className="btn-danger" onClick={(e) => { e.stopPropagation(); handleRemove(item.symbol); }} disabled={item.is_pending} style={{ padding: '4px 8px', fontSize: '12px' }}>
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

/* ─── PERX Page ─────────────────────────────────────────── */
type PerxTab = 'scan' | 'compare' | 'archive';

function PerxPage() {
  const [tab, setTab] = useState<PerxTab>('scan');
  const [query, setQuery] = useState('');
  const [symbol, setSymbol] = useState('');
  const [includeDebate, setIncludeDebate] = useState(true);
  const [loading, setLoading] = useState(false);
  const [emailing, setEmailing] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [activeReport, setActiveReport] = useState<any>(null);
  const [recentReports, setRecentReports] = useState<any[]>([]);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Safe initialization for all arrays
  const [portfolioSymbols, setPortfolioSymbols] = useState<string[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  
  // Compare state
  const [queryB, setQueryB] = useState('');
  const [symbolB, setSymbolB] = useState('');
  const [suggestionsB, setSuggestionsB] = useState<any[]>([]);
  const [showSuggestionsB, setShowSuggestionsB] = useState(false);
  const [comparison, setComparison] = useState<any>(null);
  const [comparing, setComparing] = useState(false);

  // Archive state
  const [archiveRows, setArchiveRows] = useState<any[]>([]);
  const [archiveTotal, setArchiveTotal] = useState(0);
  const [archivePage, setArchivePage] = useState(0);
  const [archiveFilter, setArchiveFilter] = useState({ symbol: '', lifecycle: '', minScore: '', maxScore: '' });
  const [archiveLoading, setArchiveLoading] = useState(false);

  // 1. Safe Data Loading
  const loadData = async () => {
    try {
      const reports = await api.getRecentPerxReports(8);
      if (Array.isArray(reports)) setRecentReports(reports);
    } catch (e) { console.error("Recent reports load failed", e); }

    try {
      const pos = await api.getPositions();
      if (pos) {
        const syms = Array.from(new Set([
          ...(pos.core_positions || []).map((p: any) => p?.symbol),
          ...(pos.swing_positions || []).map((p: any) => p?.symbol)
        ])).filter(Boolean) as string[];
        setPortfolioSymbols(syms);
      }
    } catch (e) { console.error("Portfolio symbols load failed", e); }
  };

  useEffect(() => { loadData(); }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (query && query.length >= 2) {
        try {
          const res = await api.searchCompanies(query);
          setSuggestions(Array.isArray(res) ? res : []);
          setShowSuggestions(true);
        } catch { setSuggestions([]); }
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (queryB && queryB.length >= 2) {
        try {
          const res = await api.searchCompanies(queryB);
          setSuggestionsB(Array.isArray(res) ? res : []);
          setShowSuggestionsB(true);
        } catch { setSuggestionsB([]); }
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [queryB]);

  const selectSuggestion = (company: any, isB = false) => {
    if (!company) return;
    if (isB) { setSymbolB(company.symbol); setQueryB(company.company_name || company.symbol); setShowSuggestionsB(false); }
    else { setSymbol(company.symbol); setQuery(company.company_name || company.symbol); setShowSuggestions(false); }
  };

  const handleScan = async (e?: any) => {
    if (e) e.preventDefault();
    let targetSym = symbol;
    if (!targetSym && query) {
      const found = suggestions.find(s => 
        s.symbol.toUpperCase() === query.toUpperCase() || 
        (s.company_name && s.company_name.toUpperCase() === query.toUpperCase())
      );
      if (found) {
        targetSym = found.symbol;
      } else {
        targetSym = query.trim().toUpperCase();
      }
    }

    if (!targetSym) { setStatus('Select a company first.'); return; }
    setLoading(true); setStatus(null);
    try {
      const result = await api.scanPerx(targetSym, includeDebate);
      setActiveReport(result);
      setStatus(`PERX report generated.`);
      loadData();
      const hist = await api.getPerxHistory(targetSym, 30);
      if (Array.isArray(hist)) setHistory(hist);
    } catch (err: any) { 
      let msg = err.message || 'Scan failed.';
      if (msg.includes('requires MRI') && targetSym.length > 10) {
        msg = `Symbol "${targetSym}" not found. Please select a valid company from the suggestions.`;
      }
      setStatus(msg);
    }
    finally { setLoading(false); }
  };

  const handleOpenReport = async (id: string) => {
    if (!id) return;
    setLoading(true); setStatus(null);
    try {
      const report = await api.getPerxReport(id);
      if (report) {
        setActiveReport({ report_id: id, report: report.report_json, meta: report });
        setSymbol(report.symbol);
        setQuery(report.company_name || report.symbol);
        const hist = await api.getPerxHistory(report.symbol, 30);
        if (Array.isArray(hist)) setHistory(hist);
      }
    } catch (err: any) { setStatus('Failed to load report.'); }
    finally { setLoading(false); }
  };

  const handleEmailReport = async () => {
    const id = activeReport?.report_id || activeReport?.meta?.id;
    if (!id) return;
    setEmailing(true);
    try { await api.emailPerxReport(id); setStatus('Email sent.'); }
    catch { setStatus('Email failed.'); }
    finally { setEmailing(false); }
  };

  const handleCompare = async (e?: any) => {
    if (e) e.preventDefault();
    
    // Resolve Symbol A
    let symA = symbol;
    if (!symA && query) {
      const found = suggestions.find(s => 
        s.symbol.toUpperCase() === query.toUpperCase() || 
        (s.company_name && s.company_name.toUpperCase() === query.toUpperCase())
      );
      symA = found ? found.symbol : query.trim().toUpperCase();
    }

    // Resolve Symbol B
    let symB = symbolB;
    if (!symB && queryB) {
      const found = suggestionsB.find(s => 
        s.symbol.toUpperCase() === queryB.toUpperCase() || 
        (s.company_name && s.company_name.toUpperCase() === queryB.toUpperCase())
      );
      symB = found ? found.symbol : queryB.trim().toUpperCase();
    }

    if (!symA || !symB) { setStatus('Select two companies.'); return; }
    setComparing(true); setStatus(null);
    try {
      const res = await api.comparePerx(symA, symB, includeDebate);
      if (res && res.comparison) {
        setComparison(res.comparison);
      } else {
        setStatus('Invalid comparison response.');
      }
    } catch (err: any) { 
      setStatus(err.message || 'Comparison failed.'); 
    }
    finally { setComparing(false); }
  };

  const handleLoadArchive = async (p = 0) => {
    setArchiveLoading(true);
    try {
      const params: any = { limit: 20, offset: p * 20 };
      if (archiveFilter.symbol) params.symbol = archiveFilter.symbol;
      if (archiveFilter.lifecycle) params.lifecycle_stage = archiveFilter.lifecycle;
      const res = await api.getPerxArchive(params);
      if (res) {
        setArchiveRows(Array.isArray(res.rows) ? res.rows : []);
        setArchiveTotal(res.total || 0);
        setArchivePage(p);
      }
    } catch { setArchiveRows([]); }
    finally { setArchiveLoading(false); }
  };

  useEffect(() => { if (tab === 'archive') handleLoadArchive(); }, [tab]);

  // FINAL EXTRACTION (Keep this at the bottom of the logic block)
  const report = activeReport?.report;
  const header = report?.header || {};
  const narrative = report?.narrative_transition || {};
  const engineOutputs = report?.engine_outputs || {};

  return (
    <div style={{ padding: '20px', color: '#e2e8f0', minHeight: '80vh' }}>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        {['scan', 'compare', 'archive'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t as PerxTab)}
            style={{
              padding: '10px 24px', borderRadius: '8px', border: '1px solid #1e293b',
              background: tab === t ? '#3b82f6' : '#0f172a', color: 'white',
              cursor: 'pointer', textTransform: 'capitalize', fontWeight: 600
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'scan' && (
        <div style={{ display: 'grid', gap: '20px' }}>
          <div style={{ padding: '24px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
            <h2 style={{ margin: '0 0 8px 0', fontSize: '1.5rem' }}>PERX Institutional Scan</h2>
            <form onSubmit={handleScan} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ position: 'relative', width: '300px' }}>
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                  placeholder="Company name or symbol..."
                  style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #334155', background: '#0f172a', color: 'white' }}
                />
                {showSuggestions && suggestions.length > 0 && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', marginTop: '4px', maxHeight: '200px', overflowY: 'auto' }}>
                    {suggestions.map((s, i) => (
                      <div key={i} onClick={() => selectSuggestion(s)} style={{ padding: '10px', cursor: 'pointer', borderBottom: '1px solid #1e293b' }} onMouseEnter={e => e.currentTarget.style.background = '#1e293b'} onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <b>{s.symbol}</b> - {s.company_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <button type="submit" disabled={loading} style={{ padding: '12px 24px', borderRadius: '8px', background: '#3b82f6', color: 'white', border: 'none', fontWeight: 700, cursor: 'pointer' }}>
                {loading ? 'Processing...' : 'Run Scan'}
              </button>
            </form>
            {portfolioSymbols.length > 0 && (
              <div style={{ marginTop: '20px' }}>
                <div style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '10px' }}>Portfolio Stocks</div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {portfolioSymbols.map(sym => (
                    <button key={sym} onClick={() => { setSymbol(sym); setQuery(sym); setShowSuggestions(false); }} style={{ padding: '6px 14px', borderRadius: '20px', border: '1px solid #334155', background: symbol === sym ? '#3b82f6' : '#0f172a', color: 'white', cursor: 'pointer' }}>{sym}</button>
                  ))}
                </div>
              </div>
            )}
          </div>
          {loading && <div style={{ padding: '20px', textAlign: 'center', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>🔄 Generating Institutional Rerating Report... Please wait.</div>}
          {status && <div style={{ padding: '12px 16px', background: status.includes('failed') || status.includes('requires') ? '#7f1d1d' : '#1e3a8a', borderRadius: '8px', border: '1px solid #334155', fontSize: '14px' }}>{status}</div>}

          {report && !loading && (
            <div style={{ display: 'grid', gap: '20px' }}>
              <div style={{ padding: '24px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.4rem' }}>{header.company_name}</h3>
                    <p style={{ color: '#94a3b8', margin: '4px 0' }}>{header.symbol} • {header.sector} • Generated {header.report_timestamp}</p>
                  </div>
                  <div style={{ padding: '10px 20px', borderRadius: '30px', background: '#2563eb', fontWeight: 800 }}>
                    PERX {header.perx_score}/100 | {header.lifecycle_phase}
                  </div>
                </div>

                {header.prior_baseline && (
                  <div style={{ padding: '12px 16px', background: '#1e3a8a30', borderRadius: '8px', borderLeft: '4px solid #3b82f6', marginBottom: '20px', fontSize: '13px' }}>
                    <b>Institutional Baseline:</b> {header.prior_baseline}
                  </div>
                )}

                <div style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '8px' }}>Executive Summary</div>
                  <p style={{ lineHeight: '1.6', background: '#0f172a', padding: '16px', borderRadius: '8px', margin: 0 }}>{report.executive_summary}</p>
                </div>

                <div style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '8px' }}>Narrative Transition</div>
                  <div style={{ display: 'grid', gap: '12px', background: '#0f172a', padding: '16px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '13px' }}><b style={{ color: '#94a3b8' }}>Previous:</b> {narrative.previous_market_perception}</div>
                    <div style={{ fontSize: '13px' }}><b style={{ color: '#60a5fa' }}>Emerging:</b> {narrative.emerging_market_perception}</div>
                    <div style={{ fontSize: '13px', color: '#cbd5e1', fontStyle: 'italic', marginTop: '4px' }}>{narrative.why_this_matters}</div>
                  </div>
                </div>

                <div style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '8px' }}>Engine Snapshot</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', border: '1px solid #1e293b' }}>
                      <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>MRI TECHNICAL</div>
                      <div style={{ fontSize: '13px' }}>Score: <b>{engineOutputs.mri?.total_score}/100</b></div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>RS: {engineOutputs.mri?.relative_strength} | Breakout: {engineOutputs.mri?.breakout_structure}</div>
                    </div>
                    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', border: '1px solid #1e293b' }}>
                      <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>QIF FUNDAMENTAL</div>
                      <div style={{ fontSize: '13px' }}>Score: <b>{engineOutputs.qif?.score}/100</b></div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>Category: {engineOutputs.qif?.category}</div>
                    </div>
                    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', border: '1px solid #1e293b' }}>
                      <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>STEE SETUP</div>
                      <div style={{ fontSize: '13px' }}>Setup: <b>{engineOutputs.stee?.setup_quality_score}</b></div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>Ready: {engineOutputs.stee?.breakout_ready ? 'YES' : 'No'}</div>
                    </div>
                    <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', border: '1px solid #1e293b' }}>
                      <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '4px' }}>THESIS FRAGILITY</div>
                      <div style={{ fontSize: '13px' }}>Level: <b style={{ color: engineOutputs.fragility?.level === 'LOW' ? '#22c55e' : (engineOutputs.fragility?.level === 'HIGH' ? '#ef4444' : '#eab308') }}>{engineOutputs.fragility?.level}</b></div>
                    </div>
                  </div>
                </div>

                {report.institutional_forensic_review && !report.institutional_forensic_review.unavailable && (
                  <div style={{ marginBottom: '24px' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '8px' }}>Institutional Forensic Review</div>
                    <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                      <p style={{ fontSize: '13px', lineHeight: '1.6', margin: '0 0 12px 0' }}>{report.institutional_forensic_review.guidance_vs_reality}</p>
                      <div style={{ fontSize: '12px', color: '#60a5fa', fontWeight: 'bold' }}>
                        Verdict: {report.institutional_forensic_review.verdict?.buy_recommendation} | Score: {report.institutional_forensic_review.verdict?.score}/10
                      </div>
                    </div>
                  </div>
                )}

                <div style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '8px' }}>Sector Intelligence</div>
                  <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>INDUSTRY RANK</div>
                        <div style={{ fontSize: '13px', fontWeight: 'bold' }}>{engineOutputs.sector?.industry_rank || 'N/A'}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>SECTOR BREADTH</div>
                        <div style={{ fontSize: '13px', fontWeight: 'bold', color: engineOutputs.sector?.industry_breadth === 'Accumulation' ? '#22c55e' : '#94a3b8' }}>{engineOutputs.sector?.industry_breadth}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>PEER CONTEXT</div>
                        <div style={{ fontSize: '11px' }}>{(engineOutputs.sector?.top_peers || []).join(', ') || 'No peers found'}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{ marginBottom: '24px' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '8px' }}>Historical Analogs</div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {(engineOutputs.analogs || []).map((a: string, i: number) => (
                      <span key={i} style={{ padding: '6px 12px', background: '#1e3a8a30', border: '1px solid #3b82f640', borderRadius: '6px', fontSize: '12px', color: '#60a5fa' }}>{a}</span>
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '8px' }}>Final Institutional Verdict</div>
                  <p style={{ lineHeight: '1.6', color: '#e2e8f0', margin: 0 }}>{report.final_institutional_verdict}</p>
                </div>

                <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                  <button onClick={handleEmailReport} disabled={emailing} style={{ padding: '10px 20px', borderRadius: '8px', background: '#3b82f6', color: 'white', border: 'none', fontWeight: 600, cursor: 'pointer', opacity: emailing ? 0.6 : 1 }}>
                    {emailing ? 'Sending Email...' : 'Email This Report'}
                  </button>
                  <a 
                    href={api.getPerxPdfUrl(activeReport.report_id || activeReport.meta?.id)} 
                    target="_blank" 
                    rel="noreferrer"
                    style={{ textDecoration: 'none', padding: '10px 20px', borderRadius: '8px', background: '#1e293b', color: 'white', border: '1px solid #334155', fontWeight: 600, cursor: 'pointer' }}
                  >
                    📥 Export PDF Memo
                  </a>
                </div>
              </div>

              {history && history.length > 1 && (
                <div style={{ padding: '24px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '12px' }}>PERX Score Trajectory</div>
                  <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '10px' }}>
                    {history.map((h, i) => (
                      <div key={i} style={{ minWidth: '100px', padding: '12px', background: '#0f172a', borderRadius: '8px', textAlign: 'center', border: '1px solid #1e293b' }}>
                        <div style={{ fontSize: '18px', fontWeight: 800, color: '#3b82f6' }}>{h.perx_score}</div>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '4px' }}>{new Date(h.created_at).toLocaleDateString()}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'compare' && (
        <div style={{ display: 'grid', gap: '20px' }}>
          <div style={{ padding: '24px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
            <h3 style={{ margin: '0 0 16px 0' }}>Institutional Side-by-Side Comparison</h3>
            <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <div style={{ position: 'relative', width: '280px' }}>
                <label style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>COMPANY A</label>
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                  placeholder="Primary symbol..."
                  style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #334155', background: '#0f172a', color: 'white' }}
                />
                {showSuggestions && suggestions.length > 0 && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', marginTop: '4px', maxHeight: '200px', overflowY: 'auto' }}>
                    {suggestions.map((s, i) => (
                      <div key={i} onClick={() => selectSuggestion(s)} style={{ padding: '10px', cursor: 'pointer', borderBottom: '1px solid #1e293b' }} onMouseEnter={e => e.currentTarget.style.background = '#1e293b'} onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <b>{s.symbol}</b> - {s.company_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ fontSize: '1.2rem', color: '#64748b', paddingBottom: '12px' }}>VS</div>
              <div style={{ position: 'relative', width: '280px' }}>
                <label style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>COMPANY B</label>
                <input
                  value={queryB}
                  onChange={e => setQueryB(e.target.value)}
                  onFocus={() => suggestionsB.length > 0 && setShowSuggestionsB(true)}
                  placeholder="Comparison symbol..."
                  style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #334155', background: '#0f172a', color: 'white' }}
                />
                {showSuggestionsB && suggestionsB.length > 0 && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', marginTop: '4px', maxHeight: '200px', overflowY: 'auto' }}>
                    {suggestionsB.map((s, i) => (
                      <div key={i} onClick={() => selectSuggestion(s, true)} style={{ padding: '10px', cursor: 'pointer', borderBottom: '1px solid #1e293b' }} onMouseEnter={e => e.currentTarget.style.background = '#1e293b'} onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <b>{s.symbol}</b> - {s.company_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <button 
                onClick={handleCompare} 
                disabled={comparing}
                style={{ padding: '12px 32px', borderRadius: '8px', background: '#3b82f6', color: 'white', border: 'none', fontWeight: 700, cursor: 'pointer', height: '48px' }}
              >
                {comparing ? 'Analysing...' : 'Compare Scores'}
              </button>
            </div>
          </div>

          {comparing && <div style={{ padding: '40px', textAlign: 'center', background: '#1e293b', borderRadius: '12px' }}>🔄 Generating Side-by-Side Institutional Comparison...</div>}

          {comparison && !comparing && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
              {/* Left Column (Symbol A) */}
              <div style={{ padding: '24px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155', borderLeft: comparison.comparison?.winner?.perx_score === 'left' ? '6px solid #22c55e' : '1px solid #334155' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h4 style={{ margin: 0, fontSize: '1.2rem' }}>{comparison.left?.company_name || comparison.left?.symbol}</h4>
                  <div style={{ padding: '4px 12px', borderRadius: '12px', background: '#2563eb', fontWeight: 'bold' }}>{comparison.left?.header?.perx_score || '0'}</div>
                </div>
                <div style={{ display: 'grid', gap: '10px', fontSize: '13px' }}>
                  <div style={{ padding: '8px', background: '#0f172a', borderRadius: '6px' }}><b>Stage:</b> {comparison.left?.lifecycle?.stage || 'N/A'}</div>
                  <div style={{ padding: '8px', background: '#0f172a', borderRadius: '6px' }}><b>MRI Score:</b> {comparison.left?.engine_outputs?.mri?.total_score || '0'}/100</div>
                  <div style={{ padding: '8px', background: '#0f172a', borderRadius: '6px' }}><b>QIF Category:</b> {comparison.left?.engine_outputs?.qif?.category || 'N/A'}</div>
                  <div style={{ padding: '8px', background: '#0f172a', borderRadius: '6px' }}><b>Fragility:</b> {comparison.left?.engine_outputs?.fragility?.level || 'N/A'}</div>
                </div>
              </div>

              {/* Right Column (Symbol B) */}
              <div style={{ padding: '24px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155', borderLeft: comparison.comparison?.winner?.perx_score === 'right' ? '6px solid #22c55e' : '1px solid #334155' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h4 style={{ margin: 0, fontSize: '1.2rem' }}>{comparison.right?.company_name || comparison.right?.symbol}</h4>
                  <div style={{ padding: '4px 12px', borderRadius: '12px', background: '#2563eb', fontWeight: 'bold' }}>{comparison.right?.header?.perx_score || '0'}</div>
                </div>
                <div style={{ display: 'grid', gap: '10px', fontSize: '13px' }}>
                  <div style={{ padding: '8px', background: '#0f172a', borderRadius: '6px' }}><b>Stage:</b> {comparison.right?.lifecycle?.stage || 'N/A'}</div>
                  <div style={{ padding: '8px', background: '#0f172a', borderRadius: '6px' }}><b>MRI Score:</b> {comparison.right?.engine_outputs?.mri?.total_score || '0'}/100</div>
                  <div style={{ padding: '8px', background: '#0f172a', borderRadius: '6px' }}><b>QIF Category:</b> {comparison.right?.engine_outputs?.qif?.category || 'N/A'}</div>
                  <div style={{ padding: '8px', background: '#0f172a', borderRadius: '6px' }}><b>Fragility:</b> {comparison.right?.engine_outputs?.fragility?.level || 'N/A'}</div>
                </div>
              </div>

              {/* Comparison Summary */}
              <div style={{ gridColumn: 'span 2', padding: '20px', background: '#1e3a8a30', borderRadius: '12px', border: '1px solid #3b82f640' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '1rem', color: '#60a5fa' }}>Institutional Differential</h4>
                <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                  {(comparison.comparison?.key_differentials || []).map((d: string, i: number) => (
                    <div key={i} style={{ fontSize: '13px', background: '#0f172a', padding: '6px 12px', borderRadius: '20px', border: '1px solid #1e293b' }}>• {d}</div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'archive' && (
        <div style={{ padding: '24px', background: '#1e293b', borderRadius: '12px' }}>
          <h3>Research Archive</h3>
          <table style={{ width: '100%', marginTop: '20px', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                <th style={{ padding: '12px' }}>Symbol</th>
                <th style={{ padding: '12px' }}>Score</th>
                <th style={{ padding: '12px' }}>Stage</th>
                <th style={{ padding: '12px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {archiveRows.map(r => (
                <tr key={r.id} style={{ borderBottom: '1px solid #0f172a' }}>
                  <td style={{ padding: '12px' }}>{r.symbol}</td>
                  <td style={{ padding: '12px', fontWeight: 700, color: '#3b82f6' }}>{r.perx_score}</td>
                  <td style={{ padding: '12px' }}>{r.lifecycle_stage}</td>
                  <td style={{ padding: '12px' }}><button onClick={() => { setTab('scan'); handleOpenReport(r.id); }} style={{ color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer' }}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ─── Main App ────────────────────────────────────────────── */
function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [showAuthPane, setShowAuthPane] = useState(false);
  const [page, setPage] = useState<'dashboard' | 'history' | 'performance' | 'riskaudit' | 'watchlist' | 'admin' | 'shadow' | 'perx'>('dashboard');
  const [selectedStock, setSelectedStock] = useState<any>(null);

  const urlParams = new URLSearchParams(window.location.search);
  const resetToken = urlParams.get('reset_token');
  const [isResetFlow, setIsResetFlow] = useState(!!resetToken);

  const handleResetComplete = () => {
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
          <button className={`nav-link ${page === 'perx' ? 'active' : ''}`} onClick={() => setPage('perx')}>
            <span className="nav-icon">🏛️</span> PERX
          </button>
          {isAdmin() && (
            <button className={`nav-link ${page === 'admin' ? 'active' : ''}`} onClick={() => setPage('admin')}>
              <span className="nav-icon">🛡️</span> Platform Intelligence
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
                      page === 'perx' ? 'PERX Institutional Scan' :
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
          {page === 'perx' && <PerxPage />}
          {page === 'admin' && <AdminDashboard onSelectStock={setSelectedStock} />}
        </div>
      </main>

      {selectedStock && (
        <StockDetailsModal
          stock={selectedStock}
          onClose={() => setSelectedStock(null)}
        />
      )}

      <nav className="mobile-nav">
        <button className={`mobile-nav-link ${page === 'dashboard' ? 'active' : ''}`} onClick={() => setPage('dashboard')}>🏠 Dash</button>
        <button className={`mobile-nav-link ${page === 'shadow' ? 'active' : ''}`} onClick={() => setPage('shadow')}>🚀 Swing</button>
        <button className={`mobile-nav-link ${page === 'riskaudit' ? 'active' : ''}`} onClick={() => setPage('riskaudit')}>🛡️ Audit</button>
        <button className={`mobile-nav-link ${page === 'watchlist' ? 'active' : ''}`} onClick={() => setPage('watchlist')}>👀 Watchlist</button>
        <button className={`mobile-nav-link ${page === 'perx' ? 'active' : ''}`} onClick={() => setPage('perx')}>🏛️ PERX</button>
        <button className="mobile-nav-link" onClick={() => { clearAuth(); setAuthed(false); }}>🚪 Logout</button>
      </nav>
    </div>
  );
}

export default App;
