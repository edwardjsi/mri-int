import React, { useState, useEffect } from 'react';
import { api, isAuthenticated, getClientName, clearAuth } from './api';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import './App.css';

/* ─── Login Page ─────────────────────────────────────────── */
function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [capital, setCapital] = useState('100000');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await api.register(email, name, password, parseFloat(capital));
      } else {
        await api.login(email, password);
      }
      onLogin();
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
          <h2 className="form-title">{isRegister ? 'Create Account' : 'Sign In'}</h2>
          {error && <div className="error-alert">{error}</div>}
          {isRegister && (
            <input type="text" placeholder="Full Name" value={name} onChange={e => setName(e.target.value)} className="form-input" required />
          )}
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} className="form-input" required />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} className="form-input" required minLength={6} />
          {isRegister && (
            <input type="number" placeholder="Initial Capital (₹)" value={capital} onChange={e => setCapital(e.target.value)} className="form-input" min="10000" />
          )}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Please wait...' : (isRegister ? 'Create Account' : 'Sign In')}
          </button>
          <p className="toggle-text">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button type="button" className="link-btn" onClick={() => { setIsRegister(!isRegister); setError(''); }}>
              {isRegister ? 'Sign In' : 'Register'}
            </button>
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

/* ─── Signal Card ────────────────────────────────────────── */
function SignalCard({ signal, onAction }: { signal: any; onAction: (id: string, action: string) => void }) {
  const isBuy = signal.action === 'BUY';
  return (
    <div className={`signal-card ${isBuy ? 'signal-buy' : 'signal-sell'}`}>
      <div className="signal-header">
        <span className="signal-symbol">{signal.symbol}</span>
        <span className={`signal-badge ${isBuy ? 'badge-buy' : 'badge-sell'}`}>{signal.action}</span>
      </div>
      <div className="signal-details">
        <div className="signal-detail"><span className="detail-label">Price</span><span className="detail-value">₹{signal.recommended_price?.toLocaleString()}</span></div>
        <div className="signal-detail"><span className="detail-label">Score</span><span className="detail-value">{signal.score}/5</span></div>
      </div>
      <div className="signal-reason">{signal.reason}</div>
      {signal.client_action ? (
        <div className={`action-status ${signal.client_action === 'EXECUTED' ? 'status-executed' : 'status-skipped'}`}>
          {signal.client_action === 'EXECUTED' ? '✅ Executed' : '⏭️ Skipped'}
          {signal.actual_price && ` @ ₹${signal.actual_price.toLocaleString()}`}
        </div>
      ) : (
        <div className="signal-actions">
          <button className="btn-execute" onClick={() => onAction(signal.id, 'EXECUTED')}>✅ Executed</button>
          <button className="btn-skip" onClick={() => onAction(signal.id, 'SKIPPED')}>⏭️ Skip</button>
        </div>
      )}
    </div>
  );
}

/* ─── Dashboard Page ─────────────────────────────────────── */
function DashboardPage() {
  const [regime, setRegime] = useState<any>(null);
  const [signals, setSignals] = useState<any>(null);
  const [screener, setScreener] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [r, s, sc] = await Promise.all([
        api.getRegime(),
        api.getTodaySignals().catch(() => ({ signals: [] })),
        api.getScreener(4).catch(() => ({ stocks: [] })),
      ]);
      setRegime(r);
      setSignals(s);
      setScreener(sc);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadData(); }, []);

  const handleAction = async (signalId: string, action: string) => {
    try {
      const sig = signals.signals.find((s: any) => s.id === signalId);
      await api.recordAction(signalId, action, sig?.recommended_price, action === 'EXECUTED' ? 10 : 0);
      loadData();
    } catch (err: any) { alert(err.message); }
  };

  if (loading) return <div className="loading">Loading dashboard...</div>;

  return (
    <div className="dashboard">
      <RegimeCard regime={regime} />

      <section className="section">
        <h2 className="section-title">Today's Signals</h2>
        {signals?.signals?.length > 0 ? (
          <div className="signals-grid">
            {signals.signals.map((s: any) => <SignalCard key={s.id} signal={s} onAction={handleAction} />)}
          </div>
        ) : (
          <div className="empty-state">No signals for today. The market may be closed or there are no actionable setups.</div>
        )}
      </section>

      <section className="section">
        <h2 className="section-title">Top Scoring Stocks (Score ≥ 4)</h2>
        {screener?.stocks?.length > 0 ? (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Score</th>
                  <th>Price</th>
                  <th>EMA 50/200</th>
                  <th>200 Slope</th>
                  <th>6M High</th>
                  <th>Volume</th>
                  <th>RS</th>
                </tr>
              </thead>
              <tbody>
                {screener.stocks.map((s: any) => (
                  <tr key={s.symbol}>
                    <td className="font-bold">{s.symbol}</td>
                    <td><span className="score-badge">{s.score}/5</span></td>
                    <td>₹{s.close?.toLocaleString()}</td>
                    <td>{s.conditions.ema_50_200 ? '✅' : '❌'}</td>
                    <td>{s.conditions.ema_200_slope ? '✅' : '❌'}</td>
                    <td>{s.conditions['6m_high'] ? '✅' : '❌'}</td>
                    <td>{s.conditions.volume ? '✅' : '❌'}</td>
                    <td>{s.conditions.relative_strength ? '✅' : '❌'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No stocks meeting minimum score criteria.</div>
        )}
      </section>
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

/* ─── Main App ────────────────────────────────────────────── */
function App() {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [page, setPage] = useState<'dashboard' | 'history' | 'performance'>('dashboard');

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
        </div>
        <div className="sidebar-footer">
          <div className="user-info">{getClientName()}</div>
          <button className="btn-logout" onClick={() => { clearAuth(); setAuthed(false); }}>Logout</button>
        </div>
      </nav>
      <main className="main-content">
        <header className="content-header">
          <h1 className="page-title">
            {page === 'dashboard' ? 'Signal Dashboard' : page === 'history' ? 'Trade History' : 'My Performance'}
          </h1>
        </header>
        <div className="content-body">
          {page === 'dashboard' && <DashboardPage />}
          {page === 'history' && <HistoryPage />}
          {page === 'performance' && <PerformancePage />}
        </div>
      </main>
    </div>
  );
}

export default App;
