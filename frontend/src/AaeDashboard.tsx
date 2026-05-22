import { useEffect, useState } from 'react';
import { api } from './api';

export default function AaeDashboard({ onBack }: { onBack: () => void }) {
  const [allCandidates, setAllCandidates] = useState<any[]>([]);
  const [watchlistSymbols, setWatchlistSymbols] = useState<string[]>([]);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [sectors, setSectors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterUniverse, setFilterUniverse] = useState('Nifty 500');

  // Digital Twin Modal State
  const [digitalTwinStock, setDigitalTwinStock] = useState<string | null>(null);
  const [emailing, setEmailing] = useState(false);
  const [digitalTwinResult, setDigitalTwinResult] = useState<any>(null);
  const [digitalTwinLoading, setDigitalTwinLoading] = useState(false);
  const [digitalTwinHistory, setDigitalTwinHistory] = useState<any[]>([]);
  const [digitalTwinHistoryLoading, setDigitalTwinHistoryLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getAaeTopCandidates().catch(() => []),
      api.getSectorHeatmap().catch(() => []),
      api.getWatchlist().catch(() => [])
    ])
    .then(([candData, sectorData, watchlistData]) => {
      setAllCandidates(candData);
      setCandidates(candData); // Default view
      setSectors(sectorData);
      setWatchlistSymbols((watchlistData || []).map((w: any) => w.symbol));
    })
    .catch(console.error)
    .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (filterUniverse === 'Watchlist') {
      const filtered = allCandidates.filter(c => watchlistSymbols.includes(c.symbol));
      setCandidates(filtered);
    } else {
      setCandidates(allCandidates);
    }
  }, [filterUniverse, allCandidates, watchlistSymbols]);

  const handleRunDigitalTwin = async (symbol: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDigitalTwinStock(symbol);
    setDigitalTwinLoading(true);
    setDigitalTwinResult(null);
    setDigitalTwinHistory([]);
    setDigitalTwinHistoryLoading(true);
    
    api.getAaeScan(symbol)
      .then(result => setDigitalTwinResult(result))
      .catch(err => setDigitalTwinResult({ error: err.message || 'Failed to run AAE scan' }))
      .finally(() => setDigitalTwinLoading(false));

    api.getAaeHistory(symbol)
      .then(history => setDigitalTwinHistory(history))
      .catch(err => console.error('Failed to fetch AAE history', err))
      .finally(() => setDigitalTwinHistoryLoading(false));
  };

  const handleEmailAAE = async () => {
    if (!digitalTwinStock) return;
    setEmailing(true);
    try {
      const res = await api.emailAaeReport(digitalTwinStock);
      alert(res.message || "Forensic report queued for email.");
    } catch (err) {
      console.error(err);
      alert("Failed to send email. Check API logs.");
    } finally {
      setEmailing(false);
    }
  };

  return (
    <div className="aae-console-wrapper">
      <style>{`
        /* Scoped CSS for AAE Console to avoid clashing with main App */
        .aae-console-wrapper {
          --ink: #f8fafc;
          --muted: #94a3b8;
          --line: #1e293b;
          --panel: #0f172a;
          --page: #0b1120;
          --soft: #1e293b;
          --blue: #38bdf8;
          --teal: #2dd4bf;
          --green: #4ade80;
          --amber: #fbbf24;
          background: var(--panel);
          color: var(--ink);
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          font-size: 14px;
          min-height: 100vh;
          text-align: left;
        }
        .aae-console-wrapper * { box-sizing: border-box; }
        .aae-console-wrapper h1, .aae-console-wrapper h2, .aae-console-wrapper h3, .aae-console-wrapper p { margin: 0; }
        .aae-app {
          display: grid;
          grid-template-columns: 248px minmax(0, 1fr);
          min-height: 100vh;
        }
        .aae-sidebar {
          background: var(--panel);
          border-right: 1px solid var(--line);
          color: var(--ink);
          padding: 22px 18px;
          display: flex;
          flex-direction: column;
          gap: 22px;
          position: sticky;
          top: 0;
          height: 100vh;
        }
        .aae-brand { display: grid; gap: 4px; }
        .aae-brand-title { font-size: 17px; font-weight: 760; letter-spacing: 0; color: var(--blue); }
        .aae-brand-subtitle { color: var(--muted); font-size: 11px; }
        .aae-nav { display: grid; gap: 6px; }
        .aae-nav button {
          width: 100%; border: 0; background: transparent; color: var(--muted);
          display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 8px;
          text-align: left; padding: 10px 10px; border-radius: 7px; cursor: pointer; font-size: 14px;
          transition: all 0.2s;
        }
        .aae-nav button.active, .aae-nav button:hover { background: var(--soft); color: var(--ink); }
        .aae-nav-icon {
          width: 22px; height: 22px; border: 1px solid var(--line); border-radius: 6px;
          display: grid; place-items: center; font-size: 11px; font-weight: 760; color: var(--blue);
        }
        .aae-nav-count { color: var(--muted); font-size: 11px; }
        .aae-sidebar-footer { margin-top: auto; border-top: 1px solid var(--line); padding-top: 16px; display: grid; gap: 10px; }
        .aae-status-line { display: flex; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 11px; }
        .aae-main { min-width: 0; display: grid; grid-template-rows: auto 1fr; background: var(--panel); }
        .aae-topbar {
          height: 70px; background: rgba(15, 23, 42, 0.8); border-bottom: 1px solid var(--line);
          display: grid; grid-template-columns: minmax(240px, 1fr) auto; align-items: center; gap: 18px;
          padding: 0 26px; position: sticky; top: 0; z-index: 10; backdrop-filter: blur(12px);
        }
        .aae-search {
          max-width: 560px; display: grid; grid-template-columns: 32px 1fr; align-items: center;
          background: var(--soft); border: 1px solid var(--line); border-radius: 7px; padding: 8px 12px; color: var(--muted);
        }
        .aae-search input { border: 0; outline: 0; background: transparent; color: var(--ink); min-width: 0; font-size: 14px;}
        .aae-top-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
        .aae-primary-button, .aae-quiet-button {
          border: 1px solid transparent; min-height: 36px; border-radius: 7px; padding: 0 12px; font-weight: 680; cursor: pointer; font-size: 13px;
          transition: all 0.2s;
        }
        .aae-primary-button { background: var(--blue); color: #000; }
        .aae-quiet-button { background: var(--soft); border-color: var(--line); color: var(--ink); }
        .aae-content { padding: 24px 26px 34px; display: grid; gap: 20px; }
        .aae-page-head { display: grid; grid-template-columns: minmax(260px, 1fr) auto; gap: 18px; align-items: end; }
        .aae-page-head h1 { font-size: 24px; letter-spacing: -0.02em; line-height: 1.2; font-weight: 800; }
        .aae-subtle { color: var(--muted); line-height: 1.5; font-size: 13px; }
        .aae-filters { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
        .aae-select { border: 1px solid var(--line); background: var(--soft); min-height: 36px; border-radius: 7px; padding: 0 10px; color: var(--ink); font-size: 13px; outline: none;}
        
        .aae-metric-grid { display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 12px; }
        .aae-panel, .aae-metric, .aae-candidate { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; }
        .aae-metric { padding: 14px; display: grid; gap: 8px; min-height: 108px; background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%); }
        .aae-metric-label { color: var(--muted); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
        .aae-metric-value { font-size: 28px; font-weight: 800; line-height: 1; color: var(--ink); }
        .aae-metric-foot { display: flex; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 11px; }
        
        .aae-positive { color: var(--green); }
        .aae-warning { color: var(--amber); }
        .aae-danger { color: var(--red); }
        
        .aae-dashboard-grid { display: grid; grid-template-columns: minmax(520px, 1.28fr) minmax(360px, 0.72fr); gap: 16px; align-items: start; }
        .aae-panel { min-width: 0; overflow: hidden; background: var(--panel); }
        .aae-panel-head { min-height: 58px; border-bottom: 1px solid var(--line); padding: 14px 16px; display: flex; justify-content: space-between; gap: 12px; align-items: center; }
        .aae-panel-title { display: grid; gap: 3px; }
        .aae-panel-title h2 { font-size: 15px; font-weight: 700; }
        .aae-panel-body { padding: 16px; }
        
        .aae-tabs { display: flex; border: 1px solid var(--line); border-radius: 7px; overflow: hidden; background: var(--soft); }
        .aae-tabs button { border: 0; background: transparent; padding: 8px 11px; cursor: pointer; color: var(--muted); min-height: 34px; font-size: 12px; transition: all 0.2s; }
        .aae-tabs button.active { color: var(--ink); background: var(--blue); color: #000; font-weight: 720; }
        
        .aae-candidate-list { display: grid; gap: 10px; }
        .aae-candidate { border-radius: 10px; display: grid; grid-template-columns: 54px minmax(160px, 1fr) repeat(2, minmax(82px, 0.45fr)) 112px; align-items: center; gap: 10px; padding: 12px; transition: transform 0.2s; cursor: pointer; }
        .aae-candidate:hover { transform: translateX(4px); background: var(--soft); }
        .aae-rank { width: 38px; height: 38px; border-radius: 8px; display: grid; place-items: center; background: rgba(45, 212, 191, 0.1); color: var(--teal); font-weight: 820; border: 1px solid rgba(45, 212, 191, 0.2); }
        .aae-company-cell { min-width: 0; display: grid; gap: 4px; }
        .aae-ticker { font-weight: 820; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--ink); }
        .aae-company-name { color: var(--muted); font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .aae-score-cell { display: grid; gap: 5px; min-width: 0; }
        .aae-score-label { color: var(--muted); font-size: 10px; text-transform: uppercase; font-weight: 700; }
        .aae-score-number { font-size: 17px; font-weight: 820; color: var(--blue); }
        
        .aae-bar { width: 100%; height: 6px; border-radius: 999px; background: var(--soft); overflow: hidden; }
        .aae-bar span { display: block; height: 100%; border-radius: inherit; background: var(--teal); }
        .aae-bar.blue span { background: var(--blue); }
        .aae-bar.amber span { background: var(--amber); }
        
        .aae-badge { display: inline-flex; align-items: center; justify-content: center; min-height: 22px; border-radius: 999px; padding: 0 9px; font-size: 11px; font-weight: 700; border: 1px solid transparent; white-space: nowrap; }
        .aae-badge.green { color: var(--green); background: rgba(74, 222, 128, 0.1); border-color: rgba(74, 222, 128, 0.2); }
        .aae-badge.blue { color: var(--blue); background: rgba(56, 189, 248, 0.1); border-color: rgba(56, 189, 248, 0.2); }
        .aae-badge.amber { color: var(--amber); background: rgba(251, 191, 36, 0.1); border-color: rgba(251, 191, 36, 0.2); }
        .aae-badge.red { color: var(--red); background: rgba(244, 63, 94, 0.1); border-color: rgba(244, 63, 94, 0.2); }
        .aae-badge.violet { color: var(--violet); background: rgba(167, 139, 250, 0.1); border-color: rgba(167, 139, 250, 0.2); }
        .aae-badge.gray { color: #52606d; background: #edf1f4; border-color: #dae2e8; }
        
        .aae-event-list { display: grid; gap: 10px; }
        .aae-event-row { box-shadow: none; padding: 12px; display: grid; gap: 8px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; grid-template-columns: 80px minmax(0, 1fr) 96px; align-items: start; }
        .aae-event-time { color: var(--muted); font-size: 12px; font-weight: 720; text-transform: uppercase; }
        .aae-event-main { display: grid; gap: 5px; min-width: 0; }
        .aae-event-main strong { font-weight: 600; }
        .aae-mini-note { color: var(--muted); font-size: 12px; line-height: 1.4; }
        
        /* Modal Overlay */
        .modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.9); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(12px); padding: 20px; }
        .modal-content { background: #1e293b; color: #f8fafc; width: 100%; max-width: 650px; max-height: 90vh; overflow-y: auto; border-radius: 16px; border: 1px solid var(--line); position: relative; padding: 32px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }
        .modal-close { position: absolute; top: 20px; right: 20px; background: none; border: 0; font-size: 24px; cursor: pointer; color: var(--muted); transition: color 0.2s; }
        .modal-close:hover { color: var(--ink); }
        .modal-title { font-size: 22px; font-weight: 800; margin-bottom: 8px; color: var(--ink); }
        .modal-header-meta { display: flex; align-items: baseline; gap: 12px; margin-bottom: 24px; }
        .stock-symbol { font-size: 18px; font-weight: 820; color: var(--blue); }
        .stock-sector { color: var(--muted); font-size: 14px; }
        
        .metric-box { background: var(--soft); padding: 18px; border-radius: 12px; border: 1px solid var(--line); }
        .metric-label { font-size: 11px; color: var(--muted); text-transform: uppercase; font-weight: 720; margin-bottom: 6px; letter-spacing: 0.05em; }
        .metric-value-large { font-size: 32px; font-weight: 820; color: var(--ink); }
        
        .aae-results-grid { display: grid; gap: 24px; }
        .aae-summary-card { background: rgba(56, 189, 248, 0.05); border-left: 4px solid var(--blue); padding: 16px; border-radius: 8px; border: 1px solid var(--line); }
        .aae-summary-title { font-weight: 800; color: var(--blue); margin-bottom: 8px; display: block; font-size: 13px; text-transform: uppercase; }
        .aae-summary-text { font-size: 14px; color: var(--ink); line-height: 1.6; opacity: 0.9; }
        
        .loading-pulse { width: 40px; height: 40px; background: var(--blue); border-radius: 50%; animation: pulse 1.5s infinite ease-in-out; margin: 0 auto 16px; }
        @keyframes pulse { 0% { transform: scale(0.8); opacity: 0.5; } 50% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(0.8); opacity: 0.5; } }
      `}</style>
      <div className="aae-app">
        <aside className="aae-sidebar">
          <div className="aae-brand">
            <div className="aae-brand-title">Amritkaal Alpha Engine</div>
            <div className="aae-brand-subtitle">AAE Analyst Console</div>
          </div>
          <nav className="aae-nav" aria-label="Primary">
            <button className="active" type="button"><span className="aae-nav-icon">D</span><span>Dashboard</span></button>
            <button type="button"><span className="aae-nav-icon">C</span><span>Candidates</span><span className="aae-nav-count">{candidates.length}</span></button>
            <button type="button" onClick={onBack}><span className="aae-nav-icon">←</span><span>Back to MRI</span></button>
          </nav>
          <div className="aae-sidebar-footer">
            <div className="aae-status-line"><span>Data foundation</span><strong>LIVE</strong></div>
            <div className="aae-status-line"><span>Pipeline state</span><strong>Step 9</strong></div>
            <div className="aae-status-line"><span>LLM agents</span><strong>Active</strong></div>
          </div>
        </aside>

        <main className="aae-main">
          <header className="aae-topbar">
            <label className="aae-search" aria-label="Search companies">
              <span>⌕</span>
              <input placeholder="Search..." aria-label="Search input" />
            </label>
            <div className="aae-top-actions">
              <button className="aae-quiet-button" type="button" onClick={onBack}>Exit AAE Console</button>
              <button className="aae-primary-button" type="button" onClick={() => window.location.reload()}>Refresh Scan</button>
            </div>
          </header>

          <section className="aae-content">
            <div className="aae-page-head">
              <div>
                <h1>AAE Research Dashboard</h1>
                <p className="aae-subtle">Ranked re-rating candidates, structural signals, and thesis-risk monitoring.</p>
              </div>
              <div className="aae-filters">
                <select className="aae-select" aria-label="Universe" value={filterUniverse} onChange={e => setFilterUniverse(e.target.value)}>
                  <option value="Nifty 500">Nifty 500</option>
                  <option value="Nifty 50">Nifty 50</option>
                  <option value="Watchlist">Watchlist</option>
                  <option value="PRDE Seed">PRDE Seed</option>
                </select>
                <select className="aae-select" aria-label="Period">
                  <option>Current Quarter</option>
                  <option>Previous Quarter</option>
                  <option>YTD</option>
                </select>
              </div>
            </div>

            <section className="aae-metric-grid">
              <div className="aae-metric">
                <div className="aae-metric-label">Strong Candidates</div>
                <div className="aae-metric-value">{candidates.filter(c => c.master_score >= 80).length}</div>
                <div className="aae-metric-foot"><span>Score above 80</span><strong className="aae-positive">Ready</strong></div>
              </div>
              <div className="aae-metric">
                <div className="aae-metric-label">Structural Alerts</div>
                <div className="aae-metric-value">{candidates.filter(c => JSON.stringify(c.reasons || []).includes("Structural")).length}</div>
                <div className="aae-metric-foot"><span>Signals active</span><strong className="aae-warning">Review</strong></div>
              </div>
              <div className="aae-metric">
                <div className="aae-metric-label">Thesis At Risk</div>
                <div className="aae-metric-value">{candidates.filter(c => JSON.stringify(c.reasons || []).includes("Penalty") || JSON.stringify(c.reasons || []).includes("Headwind") || c.master_score < 50).length}</div>
                <div className="aae-metric-foot"><span>Persistent red flags</span><strong className="aae-danger">Review</strong></div>
              </div>
              <div className="aae-metric">
                <div className="aae-metric-label">PRDE Coverage</div>
                <div className="aae-metric-value">25</div>
                <div className="aae-metric-foot"><span>Seed companies</span><strong className="aae-positive">Ready</strong></div>
              </div>
              <div className="aae-metric">
                <div className="aae-metric-label">Total Scanned</div>
                <div className="aae-metric-value">{candidates.length}</div>
                <div className="aae-metric-foot"><span>Top picks displayed</span><strong className="aae-blue">Live</strong></div>
              </div>
            </section>

            <section className="aae-dashboard-grid">
              <div className="aae-panel">
                <div className="aae-panel-head">
                  <div className="aae-panel-title">
                    <h2>Ranked Re-Rating Candidates</h2>
                    <p className="aae-subtle">AAE score combines structural signals, market context, and narrative shifts.</p>
                  </div>
                  <div className="aae-tabs">
                    <button className="active" type="button">Live DB Feed</button>
                  </div>
                </div>
                <div className="aae-panel-body aae-candidate-list">
                  {loading ? <p>Loading Live Candidates...</p> : candidates.map((cand, idx) => (
                    <article className="aae-candidate" key={cand.symbol} onClick={(e) => handleRunDigitalTwin(cand.symbol, e)} style={{ cursor: 'pointer' }}>
                      <div className="aae-rank">{idx + 1}</div>
                      <div className="aae-company-cell">
                        <div className="aae-ticker">{cand.symbol}</div>
                        <div className="aae-company-name">{cand.sector || 'General'}</div>
                      </div>
                      <div className="aae-score-cell">
                        <span className="aae-score-label">AAE Master</span>
                        <span className="aae-score-number">{cand.master_score}</span>
                        <div className="aae-bar"><span style={{ width: `${cand.master_score}%` }}></span></div>
                      </div>
                      <div className="aae-score-cell">
                        <span className="aae-score-label">Ownership</span>
                        <span className={`aae-score-number ${cand.ownership_status === 'STRONG' ? 'aae-positive' : 'aae-warning'}`}>{cand.ownership_status?.charAt(0)}</span>
                        <div className={`aae-bar ${cand.ownership_status === 'STRONG' ? 'blue' : 'amber'}`}><span style={{ width: cand.ownership_status === 'STRONG' ? '85%' : '40%' }}></span></div>
                      </div>
                      <span className={`aae-badge ${cand.master_score >= 80 ? 'green' : cand.master_score >= 60 ? 'amber' : 'red'}`}>
                        {cand.master_score >= 80 ? 'Strong' : cand.master_score >= 60 ? 'Review' : 'Weak'}
                      </span>
                    </article>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="aae-panel">
                  <div className="aae-panel-head">
                    <div className="aae-panel-title">
                      <h2>Live Intelligence Stream</h2>
                      <p className="aae-subtle">Top Drivers & Reasons from the V3 Engine.</p>
                    </div>
                    <span className="aae-badge gray">Live</span>
                  </div>
                  <div className="aae-panel-body aae-event-list">
                    {candidates.slice(0, 5).map((cand, idx) => (
                      <div className="aae-event-row" key={'event'+idx} onClick={(e) => handleRunDigitalTwin(cand.symbol, e)} style={{ cursor: 'pointer' }}>
                        <div className="aae-event-time">{cand.symbol}</div>
                        <div className="aae-event-main">
                          <strong>Master Score: {cand.master_score}</strong>
                          <span className="aae-mini-note">
                            {cand.reasons ? (typeof cand.reasons === 'string' ? JSON.parse(cand.reasons) : cand.reasons).slice(0,2).join(" • ") : 'No specific drivers'}
                          </span>
                        </div>
                        <span className={`aae-badge ${cand.master_score >= 80 ? 'green' : 'blue'}`}>Score</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="aae-panel">
                  <div className="aae-panel-head">
                    <div className="aae-panel-title">
                      <h2>Sector Lens</h2>
                      <p className="aae-subtle">Phase 3 Relative Benchmark (90d RS).</p>
                    </div>
                    <span className="aae-badge blue">Heatmap</span>
                  </div>
                  <div className="aae-panel-body aae-event-list">
                    {sectors.map((sec, idx) => {
                      const rs = Number(sec.relative_strength_90d) || 0;
                      const uptrend = sec.ema_50 > sec.ema_200;
                      return (
                        <div className="aae-event-row" key={'sec'+idx}>
                          <div className="aae-event-time" style={{ width: '80px', fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sec.sector_name}</div>
                          <div className="aae-event-main">
                            <strong>{sec.nse_ticker}</strong>
                            <span className="aae-mini-note">
                              {uptrend ? '📈 Uptrend' : '📉 Downtrend'} • 90d RS: {(rs * 100).toFixed(1)}%
                            </span>
                          </div>
                          <span className={`aae-badge ${rs > 0 ? 'green' : 'red'}`}>{rs > 0 ? 'Leading' : 'Lagging'}</span>
                        </div>
                      )
                    })}
                    {sectors.length === 0 && !loading && <p className="aae-subtle" style={{ padding: '12px' }}>No sector data yet.</p>}
                  </div>
                </div>
              </div>
            </section>
          </section>
        </main>

        {digitalTwinStock && (
          <div className="modal-overlay" onClick={() => !digitalTwinLoading && setDigitalTwinStock(null)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <button className="modal-close" onClick={() => !digitalTwinLoading && setDigitalTwinStock(null)}>×</button>
              <h2 className="modal-title">🤖 Digital Twin: Institutional Scan</h2>
              <div className="modal-header-meta">
                <span className="stock-symbol">{digitalTwinStock}</span>
                <span className="stock-sector">AAE V3 Forensic Audit</span>
              </div>
              
              {digitalTwinLoading ? (
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                  <div className="loading-pulse"></div>
                  <p style={{ fontWeight: 720 }}>Synchronizing Institutional Intelligence...</p>
                  <p style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '8px' }}>Running Narrative Sentiment, Structural Delta & 10-Layer Institutional Audit</p>
                </div>
              ) : digitalTwinResult ? (
                <div className="aae-results-grid">
                  {digitalTwinResult.error ? (
                    <div className="aae-summary-card" style={{ background: '#fff1f2', borderLeftColor: '#e11d48' }}>
                      <strong className="aae-summary-title" style={{ color: '#9f1239' }}>Scan Interrupted</strong>
                      <p className="aae-summary-text">{digitalTwinResult.error}</p>
                    </div>
                  ) : (
                    <>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div className="metric-box">
                          <div className="metric-label">AAE Master Score</div>
                          <div className="metric-value-large" style={{ color: digitalTwinResult.master_score >= 80 ? 'var(--green)' : 'var(--blue)' }}>
                            {digitalTwinResult.master_score}
                          </div>
                        </div>
                        <div className="metric-box">
                          <div className="metric-label">V3 Scan Status</div>
                          <div className="metric-value-large" style={{ color: 'var(--teal)' }}>
                            {digitalTwinResult.status || 'ACTIVE'}
                          </div>
                        </div>
                      </div>

                      <div className="aae-summary-card">
                        <strong className="aae-summary-title">Institutional Truth Layer</strong>
                        <p className="aae-summary-text">
                          High-conviction 10-layer forensic audit complete. System cross-referenced Structural Delta, Narrative Sentiment, and Ownership confirmation to generate the master rerating score.
                        </p>
                        <div style={{ marginTop: '12px', fontSize: '11px', color: 'var(--muted)', display: 'flex', gap: '8px' }}>
                          <span className="aae-badge blue">Forensic Source: {digitalTwinResult.narrative_source || 'SYNTHETIC_PROXY'}</span>
                          {digitalTwinResult.divergence_penalty > 0 && <span className="aae-badge red">Divergence Penalty: -{digitalTwinResult.divergence_penalty} pts</span>}
                        </div>
                      </div>

                      {digitalTwinResult.reasons && digitalTwinResult.reasons.length > 0 && (
                        <div>
                          <div className="metric-label" style={{ marginBottom: '10px' }}>Key Structural Drivers</div>
                          <div style={{ display: 'grid', gap: '8px' }}>
                            {digitalTwinResult.reasons.map((r: string, i: number) => (
                              <div key={i} style={{ padding: '10px 14px', background: 'var(--soft)', borderRadius: '6px', fontSize: '13px' }}>
                                • {r}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {digitalTwinResult.bull_case && (
                        <div style={{ marginTop: '24px', borderTop: '1px solid var(--line)', paddingTop: '20px' }}>
                          <div className="metric-label" style={{ marginBottom: '12px' }}>Institutional Bull Signal</div>
                          <div style={{ background: 'rgba(34, 197, 94, 0.05)', border: '1px solid rgba(34, 197, 94, 0.2)', padding: '16px', borderRadius: '10px', marginBottom: '16px' }}>
                            <div style={{ fontSize: '11px', color: '#22c55e', fontWeight: 800, textTransform: 'uppercase', marginBottom: '8px' }}>
                              🐂 Top Bull Case
                            </div>
                            <div style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                              {(digitalTwinResult.bull_case || '').split('\n').filter((l: string) => l.trim().startsWith('-') || l.trim().startsWith('•'))[0] || (digitalTwinResult.bull_case || '').split('\n')[0]}
                            </div>
                          </div>
                          <div style={{ textAlign: 'center' }}>
                            <button
                              onClick={handleEmailAAE}
                              disabled={emailing}
                              style={{
                                background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)',
                                border: '1px solid #4338ca',
                                padding: '10px 24px',
                                borderRadius: '8px',
                                color: 'white',
                                fontWeight: 700,
                                cursor: 'pointer',
                                fontSize: '13px'
                              }}
                            >
                              {emailing ? '📨 Sending…' : '📧 Get Full 10-Point Report by Email'}
                            </button>
                          </div>
                        </div>
                      )}

                      <div style={{ borderTop: '1px solid var(--line)', paddingTop: '20px', marginTop: '24px' }}>
                        <div className="metric-label" style={{ marginBottom: '12px' }}>Score Trajectory</div>
                        {digitalTwinHistoryLoading ? (
                          <p className="aae-subtle">Fetching history...</p>
                        ) : digitalTwinHistory.length > 0 ? (
                          <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid var(--line)', borderRadius: '8px' }}>
                            <table style={{ width: '100%', fontSize: '12px', textAlign: 'left', borderCollapse: 'collapse' }}>
                              <thead>
                                <tr style={{ background: 'var(--soft)', borderBottom: '1px solid var(--line)' }}>
                                  <th style={{ padding: '10px' }}>Date</th>
                                  <th style={{ padding: '10px' }}>Score</th>
                                  <th style={{ padding: '10px' }}>Source</th>
                                </tr>
                              </thead>
                              <tbody>
                                {digitalTwinHistory.map((h: any, i: number) => (
                                  <tr key={i} style={{ borderBottom: '1px solid var(--line)' }}>
                                    <td style={{ padding: '10px' }}>{new Date(h.scanned_at).toLocaleDateString()}</td>
                                    <td style={{ padding: '10px', fontWeight: 800 }}>{h.master_score}</td>
                                    <td style={{ padding: '10px', color: 'var(--muted)' }}>{h.scan_source}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p className="aae-subtle">First institutional scan in progress.</p>
                        )}
                      </div>

                      <div style={{ marginTop: '24px', display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
                        <button 
                          className="btn-primary" 
                          onClick={handleEmailAAE}
                          disabled={emailing}
                          style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)', border: '1px solid #4338ca', padding: '12px', borderRadius: '8px', color: 'white', fontWeight: 700, cursor: 'pointer' }}
                        >
                          {emailing ? '📨 Sending...' : '🤖 Run 10-Layer AAE Audit'}
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
