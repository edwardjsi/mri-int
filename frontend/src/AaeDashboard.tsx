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

  // Free-form Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchSymbol, setSearchSymbol] = useState('');
  const [searchSuggestions, setSearchSuggestions] = useState<any[]>([]);
  const [showSearchSuggestions, setShowSearchSuggestions] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchStatus, setSearchStatus] = useState<string | null>(null);

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

  // Debounced company search for free-form input
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (searchQuery && searchQuery.length >= 2) {
        try {
          const res = await api.searchCompanies(searchQuery);
          setSearchSuggestions(Array.isArray(res) ? res : []);
          setShowSearchSuggestions(true);
        } catch { setSearchSuggestions([]); }
      } else {
        setSearchSuggestions([]);
        setShowSearchSuggestions(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const selectSearchSuggestion = (company: any) => {
    if (!company) return;
    setSearchSymbol(company.symbol);
    setSearchQuery(company.company_name || company.symbol);
    setShowSearchSuggestions(false);
  };

  const handleSearchAndEmail = async (e?: any) => {
    if (e) e.preventDefault();
    let targetSym = searchSymbol;
    if (!targetSym && searchQuery) {
      const found = searchSuggestions.find((s: any) =>
        s.symbol.toUpperCase() === searchQuery.toUpperCase() ||
        (s.company_name && s.company_name.toUpperCase() === searchQuery.toUpperCase())
      );
      targetSym = found ? found.symbol : searchQuery.trim().toUpperCase();
    }
    if (!targetSym) { setSearchStatus('Enter a company name or symbol.'); return; }
    setSearchLoading(true); setSearchStatus(null);
    try {
      const res = await api.emailAaeReport(targetSym);
      setSearchStatus(res.message || 'Re-Rating Report queued for email.');
    } catch (err: any) {
      setSearchStatus(err.message || 'Failed to send. Check API logs.');
    } finally { setSearchLoading(false); }
  };

  const handleRunDigitalTwin = async (symbol: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDigitalTwinStock(symbol);
    setDigitalTwinLoading(true);
    setDigitalTwinResult(null);
    
    api.getAaeScan(symbol)
      .then(result => setDigitalTwinResult(result))
      .catch(err => setDigitalTwinResult({ error: err.message || 'Failed to run AAE scan' }))
      .finally(() => setDigitalTwinLoading(false));
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
            <form onSubmit={handleSearchAndEmail} style={{ display: 'flex', gap: '8px', alignItems: 'center', flex: 1 }}>
              <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
                <input
                  value={searchQuery}
                  onChange={e => { setSearchQuery(e.target.value); setSearchSymbol(''); }}
                  onFocus={() => searchSuggestions.length > 0 && setShowSearchSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSearchSuggestions(false), 200)}
                  placeholder="Company name or symbol..."
                  aria-label="Search companies"
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)', background: '#0f172a', color: 'var(--ink)', fontSize: '13px' }}
                />
                {showSearchSuggestions && searchSuggestions.length > 0 && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 200, background: '#0f172a', border: '1px solid var(--line)', borderRadius: '6px', marginTop: '4px', maxHeight: '200px', overflowY: 'auto' }}>
                    {searchSuggestions.map((s: any, i: number) => (
                      <div key={i} onMouseDown={() => selectSearchSuggestion(s)} style={{ padding: '10px', cursor: 'pointer', borderBottom: '1px solid var(--line)', color: 'var(--ink)' }} onMouseEnter={e => (e.currentTarget.style.background = '#1e293b')} onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                        <b>{s.symbol}</b> — {s.company_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <button type="submit" disabled={searchLoading} style={{ padding: '8px 16px', borderRadius: '6px', background: 'linear-gradient(135deg, #1e1b4b, #312e81)', color: 'white', border: '1px solid #4338ca', fontWeight: 700, fontSize: '13px', cursor: 'pointer', whiteSpace: 'nowrap', opacity: searchLoading ? 0.6 : 1 }}>
                {searchLoading ? 'Scanning...' : '🔍 Scan & Email'}
              </button>
              {searchStatus && <span style={{ fontSize: '11px', color: 'var(--teal)', whiteSpace: 'nowrap', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{searchStatus}</span>}
            </form>
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
                        <span className="aae-score-label">Re-Rating</span>
                        <span className="aae-score-number">{cand.master_score}</span>
                        <div className="aae-bar"><span style={{ width: `${cand.master_score}%` }}></span></div>
                      </div>
                      <div className="aae-score-cell">
                        <span className="aae-score-label">Risk</span>
                        <span className={`aae-score-number ${cand.risk_level === 'CLEAN' ? 'aae-positive' : 'aae-warning'}`}>{cand.risk_level?.charAt(0) || '?'}</span>
                        <div className={`aae-bar ${cand.risk_level === 'CLEAN' ? 'blue' : 'amber'}`}><span style={{ width: cand.risk_level === 'CLEAN' ? '85%' : '40%' }}></span></div>
                      </div>
                      <span className={`aae-badge ${(cand.master_score || 0) >= 65 ? 'green' : (cand.master_score || 0) >= 50 ? 'amber' : 'red'}`}>
                        {(cand.master_score || 0) >= 65 ? 'Rerating' : (cand.master_score || 0) >= 50 ? 'Monitor' : 'Weak'}
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
                          <strong>Re-Rating Score: {cand.master_score}</strong>
                          <span className="aae-mini-note">
                            {cand.thesis_summary || cand.thesis || 'No thesis'} • Risk: {cand.risk_level || '—'}
                          </span>
                        </div>
                        <span className={`aae-badge ${(cand.master_score || 0) >= 65 ? 'green' : 'blue'}`}>Score</span>
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
                  <p style={{ fontWeight: 720 }}>Synthesizing Re-Rating Profile...</p>
                  <p style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '8px' }}>Running Governance, PRDE, Structural, Macro & Risk layers</p>
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
                          <div className="metric-label">Re-Rating Probability</div>
                          <div className="metric-value-large" style={{ color: (digitalTwinResult.rerating_probability_score || 0) >= 65 ? 'var(--green)' : 'var(--blue)' }}>
                            {digitalTwinResult.rerating_probability_score ?? '—'}
                          </div>
                        </div>
                        <div className="metric-box">
                          <div className="metric-label">Score Interpretation</div>
                          <div className="metric-value-large" style={{ fontSize: '18px', color: 'var(--teal)' }}>
                            {digitalTwinResult.score_interpretation || 'Not available'}
                          </div>
                        </div>
                      </div>

                      {/* Thesis Verdict */}
                      <div className="aae-summary-card">
                        <strong className="aae-summary-title">Investment Thesis</strong>
                        <p className="aae-summary-text">
                          {digitalTwinResult.thesis?.summary || 'Thesis unavailable'}
                        </p>
                      </div>

                      {/* Layer Scores */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
                        <div style={{ background: 'var(--soft)', padding: '12px', borderRadius: '8px', border: '1px solid var(--line)', textAlign: 'center' }}>
                          <div style={{ fontSize: '10px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 700 }}>PRDE</div>
                          <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--blue)', marginTop: '4px' }}>{digitalTwinResult.master_checklist_score ?? '—'}</div>
                        </div>
                        <div style={{ background: 'var(--soft)', padding: '12px', borderRadius: '8px', border: '1px solid var(--line)', textAlign: 'center' }}>
                          <div style={{ fontSize: '10px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 700 }}>Structural</div>
                          <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--teal)', marginTop: '4px' }}>{digitalTwinResult.structural_conviction_score ?? '—'}</div>
                        </div>
                        <div style={{ background: 'var(--soft)', padding: '12px', borderRadius: '8px', border: '1px solid var(--line)', textAlign: 'center' }}>
                          <div style={{ fontSize: '10px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 700 }}>Macro</div>
                          <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--amber)', marginTop: '4px' }}>{digitalTwinResult.macro_alignment_score ?? '—'}</div>
                        </div>
                        <div style={{ background: 'var(--soft)', padding: '12px', borderRadius: '8px', border: '1px solid var(--line)', textAlign: 'center' }}>
                          <div style={{ fontSize: '10px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 700 }}>Risk</div>
                          <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--red)', marginTop: '4px' }}>{digitalTwinResult.risk_level || '—'}</div>
                        </div>
                      </div>

                      {/* Reasons from thesis */}
                      {digitalTwinResult.thesis?.reasons && digitalTwinResult.thesis.reasons.length > 0 && (
                        <div>
                          <div className="metric-label" style={{ marginBottom: '10px' }}>Reasons for Re-Rating Thesis</div>
                          <div style={{ display: 'grid', gap: '8px' }}>
                            {digitalTwinResult.thesis.reasons.map((r: string, i: number) => (
                              <div key={i} style={{ padding: '10px 14px', background: 'rgba(74, 222, 128, 0.05)', borderLeft: '3px solid var(--green)', borderRadius: '6px', fontSize: '13px' }}>
                                + {r}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Risks from thesis */}
                      {digitalTwinResult.thesis?.risks && digitalTwinResult.thesis.risks.length > 0 && (
                        <div>
                          <div className="metric-label" style={{ marginBottom: '10px' }}>Risk Flags</div>
                          <div style={{ display: 'grid', gap: '8px' }}>
                            {digitalTwinResult.thesis.risks.map((r: string, i: number) => (
                              <div key={i} style={{ padding: '10px 14px', background: 'rgba(244, 63, 94, 0.05)', borderLeft: '3px solid var(--red)', borderRadius: '6px', fontSize: '13px' }}>
                                — {r}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Active Signals */}
                      {digitalTwinResult.structural_signals?.active_signals && digitalTwinResult.structural_signals.active_signals.length > 0 && (
                        <div>
                          <div className="metric-label" style={{ marginBottom: '10px' }}>Active Structural Signals ({digitalTwinResult.structural_signals.active_count}/6)</div>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {digitalTwinResult.structural_signals.active_signals.map((s: string, i: number) => (
                              <span key={i} className="aae-badge green">{s.replace(/_/g, ' ')}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Macro Outlook */}
                      {digitalTwinResult.macro_alignment && (
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '14px', background: 'var(--soft)', borderRadius: '8px', border: '1px solid var(--line)' }}>
                          <span className="metric-label" style={{ margin: 0 }}>Macro Outlook</span>
                          <span className={`aae-badge ${(digitalTwinResult.macro_alignment.outlook || '').startsWith('STRONG') ? 'green' : (digitalTwinResult.macro_alignment.outlook || '').includes('HEADWIND') ? 'red' : 'blue'}`}>
                            {digitalTwinResult.macro_alignment.outlook || 'Neutral'}
                          </span>
                          <span style={{ color: 'var(--muted)', fontSize: '12px', marginLeft: 'auto' }}>
                            {digitalTwinResult.macro_alignment.sector} • {digitalTwinResult.macro_alignment.macro_alignment_score}/100
                          </span>
                        </div>
                      )}

                      {/* Risk Alerts */}
                      {digitalTwinResult.risk_state?.alerts && digitalTwinResult.risk_state.alerts.length > 0 && (
                        <div>
                          <div className="metric-label" style={{ marginBottom: '10px' }}>Active Risk Alerts ({digitalTwinResult.risk_state.overall_risk_state})</div>
                          <div style={{ display: 'grid', gap: '6px' }}>
                            {digitalTwinResult.risk_state.alerts.map((a: any, i: number) => (
                              <div key={i} style={{ padding: '10px 14px', background: a.severity === 'RED' ? 'rgba(244, 63, 94, 0.08)' : 'rgba(251, 191, 36, 0.08)', borderRadius: '6px', fontSize: '13px', border: '1px solid var(--line)' }}>
                                <strong>[{a.severity}] {a.category.replace(/_/g, ' ')}</strong> — {a.detail}{a.data_source ? <span style={{ color: 'var(--muted)', fontSize: '11px', marginLeft: '8px' }}>({a.data_source})</span> : null}
                                {a.suggested_action ? <div style={{ marginTop: '4px', fontSize: '11px', color: 'var(--amber)' }}>→ {a.suggested_action}</div> : null}
                              </div>
                            ))}
                          </div>
                      </div>
                      )}

                      <div style={{ marginTop: '24px', display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
                        <button 
                          className="btn-primary" 
                          onClick={handleEmailAAE}
                          disabled={emailing}
                          style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)', border: '1px solid #4338ca', padding: '12px', borderRadius: '8px', color: 'white', fontWeight: 700, cursor: 'pointer' }}
                        >
                          {emailing ? '📨 Sending...' : '📧 Email Full Re-Rating Report'}
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
