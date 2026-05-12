import { useEffect, useState } from 'react';
import { api } from './api';

export default function AaeDashboard({ onBack }: { onBack: () => void }) {
  const [candidates, setCandidates] = useState<any[]>([]);
  const [sectors, setSectors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterUniverse, setFilterUniverse] = useState('Nifty 500');

  useEffect(() => {
    Promise.all([
      api.getAaeTopCandidates().catch(() => []),
      api.getSectorHeatmap().catch(() => [])
    ])
    .then(([candData, sectorData]) => {
      setCandidates(candData);
      setSectors(sectorData);
    })
    .catch(console.error)
    .finally(() => setLoading(false));
  }, []);

  return (
    <div className="aae-console-wrapper">
      <style>{`
        /* Scoped CSS for AAE Console to avoid clashing with main App */
        .aae-console-wrapper {
          --ink: #17202a;
          --muted: #64707d;
          --line: #dbe1e7;
          --panel: #ffffff;
          --page: #f4f6f8;
          --soft: #eef3f7;
          --blue: #255e9c;
          --teal: #0f766e;
          --green: #16803d;
          --amber: #a15c00;
          --red: #b42318;
          --violet: #6251a3;
          --shadow: 0 14px 35px rgba(28, 39, 49, 0.08);
          background: var(--page);
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
          background: #14222f;
          color: #dfe8ef;
          padding: 22px 18px;
          display: flex;
          flex-direction: column;
          gap: 22px;
          position: sticky;
          top: 0;
          height: 100vh;
        }
        .aae-brand { display: grid; gap: 4px; }
        .aae-brand-title { font-size: 17px; font-weight: 760; letter-spacing: 0; }
        .aae-brand-subtitle { color: #98a9b6; font-size: 12px; }
        .aae-nav { display: grid; gap: 6px; }
        .aae-nav button {
          width: 100%; border: 0; background: transparent; color: #bfccd6;
          display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 8px;
          text-align: left; padding: 10px 10px; border-radius: 7px; cursor: pointer; font-size: 14px;
        }
        .aae-nav button.active, .aae-nav button:hover { background: #213446; color: #ffffff; }
        .aae-nav-icon {
          width: 22px; height: 22px; border: 1px solid rgba(255,255,255,0.18); border-radius: 6px;
          display: grid; place-items: center; font-size: 11px; font-weight: 760; color: #dbe7ef;
        }
        .aae-nav-count { color: #94a7b7; font-size: 12px; }
        .aae-sidebar-footer { margin-top: auto; border-top: 1px solid rgba(255,255,255,0.12); padding-top: 16px; display: grid; gap: 10px; }
        .aae-status-line { display: flex; justify-content: space-between; gap: 8px; color: #b9c8d3; font-size: 12px; }
        .aae-main { min-width: 0; display: grid; grid-template-rows: auto 1fr; }
        .aae-topbar {
          height: 70px; background: rgba(255,255,255,0.92); border-bottom: 1px solid var(--line);
          display: grid; grid-template-columns: minmax(240px, 1fr) auto; align-items: center; gap: 18px;
          padding: 0 26px; position: sticky; top: 0; z-index: 3; backdrop-filter: blur(12px);
        }
        .aae-search {
          max-width: 560px; display: grid; grid-template-columns: 32px 1fr; align-items: center;
          background: var(--soft); border: 1px solid var(--line); border-radius: 7px; padding: 8px 12px; color: var(--muted);
        }
        .aae-search input { border: 0; outline: 0; background: transparent; color: var(--ink); min-width: 0; font-size: 14px;}
        .aae-top-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
        .aae-primary-button, .aae-quiet-button {
          border: 1px solid transparent; min-height: 36px; border-radius: 7px; padding: 0 12px; font-weight: 680; cursor: pointer; font-size: 14px;
        }
        .aae-primary-button { background: var(--blue); color: #fff; }
        .aae-quiet-button { background: #fff; border-color: var(--line); color: var(--ink); }
        .aae-content { padding: 24px 26px 34px; display: grid; gap: 20px; }
        .aae-page-head { display: grid; grid-template-columns: minmax(260px, 1fr) auto; gap: 18px; align-items: end; }
        .aae-page-head h1 { font-size: 25px; letter-spacing: 0; line-height: 1.2; }
        .aae-subtle { color: var(--muted); line-height: 1.5; }
        .aae-filters { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
        .aae-select { border: 1px solid var(--line); background: #fff; min-height: 36px; border-radius: 7px; padding: 0 10px; color: var(--ink); font-size: 14px;}
        
        .aae-metric-grid { display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 12px; }
        .aae-panel, .aae-metric, .aae-candidate { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); }
        .aae-metric { padding: 14px; display: grid; gap: 8px; min-height: 108px; }
        .aae-metric-label { color: var(--muted); font-size: 12px; font-weight: 680; text-transform: uppercase; }
        .aae-metric-value { font-size: 28px; font-weight: 800; line-height: 1; }
        .aae-metric-foot { display: flex; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 12px; }
        
        .aae-positive { color: var(--green); }
        .aae-warning { color: var(--amber); }
        .aae-danger { color: var(--red); }
        
        .aae-dashboard-grid { display: grid; grid-template-columns: minmax(520px, 1.28fr) minmax(360px, 0.72fr); gap: 16px; align-items: start; }
        .aae-panel { min-width: 0; overflow: hidden; }
        .aae-panel-head { min-height: 58px; border-bottom: 1px solid var(--line); padding: 14px 16px; display: flex; justify-content: space-between; gap: 12px; align-items: center; }
        .aae-panel-title { display: grid; gap: 3px; }
        .aae-panel-title h2 { font-size: 16px; letter-spacing: 0; }
        .aae-panel-body { padding: 16px; }
        
        .aae-tabs { display: flex; border: 1px solid var(--line); border-radius: 7px; overflow: hidden; background: #fff; }
        .aae-tabs button { border: 0; background: transparent; padding: 8px 11px; cursor: pointer; color: var(--muted); min-height: 34px; font-size: 13px;}
        .aae-tabs button.active { color: var(--ink); background: var(--soft); font-weight: 720; }
        
        .aae-candidate-list { display: grid; gap: 10px; }
        .aae-candidate { box-shadow: none; display: grid; grid-template-columns: 54px minmax(160px, 1fr) repeat(2, minmax(82px, 0.45fr)) 112px; align-items: center; gap: 10px; padding: 12px; }
        .aae-rank { width: 38px; height: 38px; border-radius: 8px; display: grid; place-items: center; background: #eef6f3; color: var(--teal); font-weight: 820; }
        .aae-company-cell { min-width: 0; display: grid; gap: 4px; }
        .aae-ticker { font-weight: 820; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .aae-company-name { color: var(--muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .aae-score-cell { display: grid; gap: 5px; min-width: 0; }
        .aae-score-label { color: var(--muted); font-size: 11px; text-transform: uppercase; font-weight: 680; }
        .aae-score-number { font-size: 18px; font-weight: 820; }
        
        .aae-bar { width: 100%; height: 7px; border-radius: 999px; background: #e8edf2; overflow: hidden; }
        .aae-bar span { display: block; height: 100%; border-radius: inherit; background: var(--teal); }
        .aae-bar.blue span { background: var(--blue); }
        .aae-bar.amber span { background: var(--amber); }
        
        .aae-badge { display: inline-flex; align-items: center; justify-content: center; min-height: 24px; border-radius: 999px; padding: 0 9px; font-size: 12px; font-weight: 760; border: 1px solid transparent; white-space: nowrap; }
        .aae-badge.green { color: #0f5d2e; background: #e8f6ee; border-color: #c8e7d3; }
        .aae-badge.blue { color: #174d82; background: #e8f1fa; border-color: #c9dbec; }
        .aae-badge.amber { color: #875000; background: #fff3df; border-color: #f3d7a5; }
        .aae-badge.red { color: #9b1c14; background: #fdecea; border-color: #f5c8c3; }
        .aae-badge.gray { color: #52606d; background: #edf1f4; border-color: #dae2e8; }
        
        .aae-event-list { display: grid; gap: 10px; }
        .aae-event-row { box-shadow: none; padding: 12px; display: grid; gap: 8px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; grid-template-columns: 80px minmax(0, 1fr) 96px; align-items: start; }
        .aae-event-time { color: var(--muted); font-size: 12px; font-weight: 720; text-transform: uppercase; }
        .aae-event-main { display: grid; gap: 5px; min-width: 0; }
        .aae-event-main strong { font-weight: 600; }
        .aae-mini-note { color: var(--muted); font-size: 12px; line-height: 1.4; }
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
                    <article className="aae-candidate" key={cand.symbol}>
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
                      <div className="aae-event-row" key={'event'+idx}>
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
      </div>
    </div>
  );
}
