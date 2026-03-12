import React, { useState, useEffect, useMemo } from 'react';
import { api, isAuthenticated, getClientName, clearAuth } from './api';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import './App.css';

/* ─── Login Page ─────────────────────────────────────────── */
function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [isRegister, setIsRegister] = useState(false);
  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [capital, setCapital] = useState('100000');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);
    try {
      if (isForgotPassword) {
        const res = await api.forgotPassword(email);
        setSuccessMsg(res.message || 'Password reset link sent! Check your email.');
      } else if (isRegister) {
        await api.register(email, name, password, parseFloat(capital));
        onLogin();
      } else {
        await api.login(email, password);
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

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Please wait...' : (isForgotPassword ? 'Send Reset Link' : (isRegister ? 'Create Account' : 'Sign In'))}
          </button>

          <div className="toggle-text" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {!isForgotPassword && (
              <button type="button" className="link-btn" style={{ alignSelf: 'center' }} onClick={() => { setIsForgotPassword(true); setError(''); setSuccessMsg(''); }}>
                Forgot your password?
              </button>
            )}

            <p>
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
        </form>
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

          <p className="toggle-text">
            <button type="button" className="link-btn" onClick={onComplete}>Back to Sign In</button>
          </p>
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
          <span className="summary-label">Overall</span>
          <span className="summary-value" style={{ color: summary.total_return >= 0 ? '#22c55e' : '#ef4444' }}>
            {summary.total_return >= 0 ? '+' : ''}₹{summary.total_return?.toLocaleString()} ({summary.total_pct}%)
          </span>
        </div>
        <div className="summary-stat">
          <span className="summary-label">Cash</span>
          <span className="summary-value">₹{summary.cash?.toLocaleString()}</span>
        </div>
        <div className="summary-stat">
          <span className="summary-label">Positions</span>
          <span className="summary-value">{summary.open_positions}/10</span>
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
function SignalCard({ signal, totalCapital, onAction }: {
  signal: any;
  totalCapital: number;
  onAction: (id: string, action: string, price?: number, qty?: number) => void;
}) {
  const [showDialog, setShowDialog] = useState(false);
  const isBuy = signal.action === 'BUY';
  const allocation = totalCapital * 0.1;
  const suggestedQty = signal.recommended_price ? Math.floor(allocation / signal.recommended_price) : 0;

  return (
    <>
      <div className={`signal-card ${isBuy ? 'signal-buy' : 'signal-sell'}`}>
        <div className="signal-header">
          <span className="signal-symbol">{signal.symbol}</span>
          <span className={`signal-badge ${isBuy ? 'badge-buy' : 'badge-sell'}`}>{signal.action}</span>
        </div>
        <div className="signal-details">
          <div className="signal-detail"><span className="detail-label">Price</span><span className="detail-value">₹{signal.recommended_price?.toLocaleString()}</span></div>
          <div className="signal-detail"><span className="detail-label">Score</span><span className="detail-value">{signal.score}/5</span></div>
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

/* ─── Dashboard Page ─────────────────────────────────────── */
function DashboardPage() {
  const [regime, setRegime] = useState<any>(null);
  const [signals, setSignals] = useState<any>(null);
  const [pending, setPending] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [showAddCapital, setShowAddCapital] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [r, s, p, sum, prof] = await Promise.all([
        api.getRegime(),
        api.getTodaySignals().catch(() => ({ signals: [] })),
        api.getPendingSignals().catch(() => []),
        api.getDailySummary().catch(() => null),
        api.getProfile().catch(() => null),
      ]);
      setRegime(r);
      setSignals(s);
      setPending(p);
      setSummary(sum);
      setProfile(prof);
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
          <div className="card-label">My Capital</div>
          <div className="capital-value">₹{totalCapital.toLocaleString()}</div>
          <div className="card-meta">
            Per stock: ₹{(totalCapital * 0.1).toLocaleString()} (10%)
          </div>
          <button className="btn-add-capital" onClick={() => setShowAddCapital(true)}>+ Add Capital</button>
        </div>
      </div>

      <DailySummaryCard summary={summary} />

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
              <SignalCard key={s.id} signal={s} totalCapital={totalCapital} onAction={handleAction} />
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
              <SignalCard key={s.id} signal={s} totalCapital={totalCapital} onAction={handleAction} />
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
function HistoryPage() {
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
                <tr key={a.id}>
                  <td>{a.signal_date}</td>
                  <td className="font-bold">{a.symbol}</td>
                  <td><span className={`signal-badge-sm ${a.signal_action === 'BUY' ? 'badge-buy' : 'badge-sell'}`}>{a.signal_action}</span></td>
                  <td><span className={`action-badge ${a.action_taken === 'EXECUTED' ? 'badge-executed' : 'badge-skipped'}`}>{a.action_taken}</span></td>
                  <td>₹{a.recommended_price?.toLocaleString()}</td>
                  <td>₹{a.actual_price?.toLocaleString()}</td>
                  <td>{a.quantity || '-'}</td>
                  <td>{a.score}/5</td>
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
          <h3 className="section-title">Open Positions</h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr><th>Symbol</th><th>Entry Date</th><th>Entry Price</th><th>Current Price</th><th>Qty</th><th>P&L %</th></tr>
              </thead>
              <tbody>
                {positions.positions.map((p: any) => (
                  <tr key={p.symbol}>
                    <td className="font-bold">{p.symbol}</td>
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
function RiskAuditPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [savedResult, setSavedResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [saveLoading, setSaveLoading] = useState(false);
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);

  const loadSavedHoldings = async () => {
    try {
      const data = await api.getSavedHoldings();
      setSavedResult(data);
    } catch (err) {
      console.error('Failed to load saved holdings', err);
    }
  };

  useEffect(() => {
    loadSavedHoldings();
  }, []);

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

  const sortedHoldings = useMemo(() => {
    if (!result?.holdings) return [];
    let sortableItems = [...result.holdings];
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
  }, [result?.holdings, sortConfig]);

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
    setResult(null);
    try {
      const data = await api.uploadPortfolioCsv(file);
      setResult(data);
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
      for (const h of result.holdings) {
        await api.saveHolding(h.symbol, h.quantity, h.avg_cost);
      }
      alert('All holdings saved successfully!');
      loadSavedHoldings();
    } catch (err: any) {
      alert(err.message || 'Failed to save holdings');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleDeleteHolding = async (symbol: string) => {
    if (!confirm(`Remove ${symbol} from your holdings?`)) return;
    try {
      await api.deleteHolding(symbol);
      loadSavedHoldings();
    } catch (err: any) {
      alert(err.message || 'Failed to delete holding');
    }
  };

  return (
    <div className="risk-audit">
      <h2 className="section-title">Portfolio Risk Audit</h2>
      <p className="section-subtitle">
        Upload your broker holdings CSV (e.g., Zerodha) to instantly analyze your portfolio's risk against our MRI framework.
      </p>

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
              Supports Zerodha, Groww, and standard portfolio CSVs
            </span>
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
            {loading ? '🔬 Analyzing Portfolio...' : 'Analyze Risk Now'}
          </button>
          
          {file && !loading && (
            <button className="link-btn" onClick={() => setFile(null)}>
              Clear selection
            </button>
          )}
        </div>
      </div>

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
              <div className="stat-label">Total Value analyzed</div>
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
                    <th title="The MRI trend score (0-5) combining moving averages, momentum, and volume" onClick={() => handleSort('score')} style={{cursor: 'pointer', userSelect: 'none'}}>Score (0-5){getSortIcon('score')}</th>
                    <th title="Whether the stock's trend aligns with the overall Market Regime" onClick={() => handleSort('alignment')} style={{cursor: 'pointer', userSelect: 'none'}}>Alignment{getSortIcon('alignment')}</th>
                    <th title="Percentage of your total portfolio value invested in this stock" onClick={() => handleSort('weight_pct')} style={{cursor: 'pointer', userSelect: 'none'}}>Weight{getSortIcon('weight_pct')}</th>
                    <th title="How much of your portfolio's total risk comes from this specific holding" onClick={() => handleSort('risk_contribution_pct')} style={{cursor: 'pointer', userSelect: 'none'}}>Risk Contribution{getSortIcon('risk_contribution_pct')}</th>
                    <th title="WARNING: Stocks trading below their 200-day Exponential Moving Average are in long-term downtrends" onClick={() => handleSort('below_200ema')} style={{cursor: 'pointer', userSelect: 'none'}}>Below 200 EMA{getSortIcon('below_200ema')}</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedHoldings.map((h: any) => (
                    <tr key={h.symbol}>
                      <td className="font-bold">{h.symbol}</td>
                      <td>{h.score !== null ? `${h.score}/5` : 'N/A'}</td>
                      <td>
                        <span className={`action-badge ${h.alignment === 'ALIGNED' || h.alignment === 'STRONG' ? 'badge-executed' : h.alignment === 'WEAK' ? 'badge-skipped' : ''}`}>
                          {h.alignment}
                        </span>
                      </td>
                      <td>{h.weight_pct}%</td>
                      <td>{h.risk_contribution_pct}%</td>
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

      {/* ── SECTION: My Saved Holdings ("The Layer") ── */}
      <section className="section" style={{ marginTop: '40px' }}>
        <h2 className="section-title">🛡️ My Holdings (Digital Twin)</h2>
        <p className="section-subtitle">
          Your persistent portfolio layer. These assets are tracked in real-time against MRI intelligence.
        </p>

        {savedResult && savedResult.holdings && savedResult.holdings.length > 0 ? (
          <>
            <div className="stats-row">
              <div className="stat-card" style={{ borderLeft: `4px solid ${savedResult.risk_level === 'EXTREME' || savedResult.risk_level === 'HIGH' ? '#ef4444' : savedResult.risk_level === 'MODERATE' ? '#eab308' : '#22c55e'}` }}>
                <div className="stat-label">Portfolio Risk</div>
                <div className="stat-value">{savedResult.risk_level}</div>
                <div className="card-meta">Score: {savedResult.risk_score_pct || '0%'}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Total Value</div>
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
                    <th>Symbol</th>
                    <th>Score</th>
                    <th>Alignment</th>
                    <th>Qty</th>
                    <th>Avg Cost</th>
                    <th>Current</th>
                    <th>P&L %</th>
                    <th>Risk Contrib</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {savedResult.holdings.map((h: any) => (
                    <tr key={h.symbol}>
                      <td className="font-bold">{h.symbol}</td>
                      <td>{h.score !== null ? `${h.score}/5` : 'N/A'}</td>
                      <td>
                        <span className={`action-badge ${h.alignment === 'ALIGNED' || h.alignment === 'STRONG' ? 'badge-executed' : h.alignment === 'WEAK' ? 'badge-skipped' : ''}`}>
                          {h.alignment}
                        </span>
                      </td>
                      <td>{h.quantity}</td>
                      <td>₹{h.avg_cost?.toLocaleString()}</td>
                      <td>₹{h.current_price?.toLocaleString()}</td>
                      <td style={{ color: (h.pnl_pct || 0) >= 0 ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                        {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct}%
                      </td>
                      <td>{h.risk_contribution_pct}%</td>
                      <td>
                        <button className="btn-skip" onClick={() => handleDeleteHolding(h.symbol)} style={{ padding: '4px 8px', fontSize: '12px' }}>
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
          <div className="empty-state">No holdings saved yet. Upload a CSV above to start your Digital Twin layer.</div>
        )}
      </section>
    </div>
  );
}

/* ─── Main App ────────────────────────────────────────────── */
function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [page, setPage] = useState<'dashboard' | 'history' | 'performance' | 'riskaudit'>('dashboard');

  // Custom simple routing for password reset link
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

  if (!authed) return <LoginPage onLogin={() => setAuthed(true)} />;

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
          <button className={`nav-link ${page === 'history' ? 'active' : ''}`} onClick={() => setPage('history')}>
            <span className="nav-icon">📋</span> History
          </button>
          <button className={`nav-link ${page === 'performance' ? 'active' : ''}`} onClick={() => setPage('performance')}>
            <span className="nav-icon">📈</span> Performance
          </button>
          <button className={`nav-link ${page === 'riskaudit' ? 'active' : ''}`} onClick={() => setPage('riskaudit')}>
            <span className="nav-icon">🛡️</span> Risk Audit
          </button>
        </div>
        <div className="sidebar-footer">
          <div className="user-info">{getClientName()}</div>
          <button className="btn-logout" onClick={() => { clearAuth(); setAuthed(false); }}>Logout</button>
        </div>
      </nav>
      <main className="main-content">
        <header className="content-header">
          <h1 className="page-title">
            {page === 'dashboard' ? 'Signal Dashboard' : page === 'history' ? 'Trade History' : page === 'riskaudit' ? 'Portfolio Risk Audit' : 'My Performance'}
          </h1>
        </header>
        <div className="content-body">
          {page === 'dashboard' && <DashboardPage />}
          {page === 'history' && <HistoryPage />}
          {page === 'performance' && <PerformancePage />}
          {page === 'riskaudit' && <RiskAuditPage />}
        </div>
      </main>
    </div>
  );
}

export default App;
