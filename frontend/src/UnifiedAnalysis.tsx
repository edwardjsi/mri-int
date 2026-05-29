import { useState, useEffect, useRef } from 'react';
import { api } from './api';

export default function UnifiedAnalysis({ onBack }: { onBack: () => void }) {
  const [symbol, setSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'overview' | 'perx' | 'aae' | 'guidance' | 'mosi'>('overview');
  const [allowedSymbols, setAllowedSymbols] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [allowedLoading, setAllowedLoading] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([
      api.getWatchlist().catch(() => []),
      api.getPositions().catch(() => []),
    ]).then(([watchlist, positions]) => {
      const wlSymbols = (watchlist || []).map((w: any) => w.symbol?.toUpperCase()).filter(Boolean);
      const posSymbols = (positions || []).map((p: any) => p.symbol?.toUpperCase()).filter(Boolean);
      const all = [...new Set([...wlSymbols, ...posSymbols])].sort();
      setAllowedSymbols(all);
      setAllowedLoading(false);
    }).catch(() => setAllowedLoading(false));
  }, []);
  // Close suggestions when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleScan = async (e?: any) => {
    if (e) e.preventDefault();
    if (!symbol.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.scanUnified(symbol.trim().toUpperCase());
      setResult(data);
      setTab('overview');
    } catch (err: any) {
      setError(err?.message || 'Scan failed');
    } finally {
      setLoading(false);
    }
  };

  const getRatingColor = (rating: string) => {
    if (rating === 'READY') return '#22c55e';
    if (rating === 'GETTING READY') return '#eab308';
    return '#ef4444';
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
        <button onClick={onBack} style={{ color: '#94a3b8', background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }}>← Back</button>
        <h2 style={{ margin: 0, fontSize: '1.5rem', color: '#f1f5f9' }}>Unified Institutional Scan</h2>
      </div>

      {/* Info Banner */}
      <div style={{ padding: '12px 16px', background: '#1e1b4b', border: '1px solid #4338ca', borderRadius: '8px', marginBottom: '16px', fontSize: '13px', color: '#c7d2fe' }}>
        🧠 <strong>Unified Scan</strong> works on stocks in your <strong>Watchlist</strong> or <strong>Digital Twin</strong> (Portfolio).
        {allowedLoading ? ' Loading your stocks…' : allowedSymbols.length === 0 ? ' Add stocks to Watchlist or Portfolio first.' : ` ${allowedSymbols.length} stock${allowedSymbols.length > 1 ? 's' : ''} available for scanning.`}
      </div>

      {/* Search */}
      <div style={{ padding: '24px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155', marginBottom: '24px' }}>
        <form onSubmit={handleScan} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              ref={inputRef}
              type="text"
              value={symbol}
              onChange={e => { setSymbol(e.target.value.toUpperCase()); setShowSuggestions(true); }}
              onFocus={() => setShowSuggestions(true)}
              placeholder="Type a symbol from your Watchlist or Portfolio…"
              autoComplete="off"
              style={{
                padding: '10px 16px', borderRadius: '8px', border: '1px solid #475569',
                background: '#0f172a', color: '#f1f5f9', fontSize: '15px', width: '100%',
                boxSizing: 'border-box'
              }}
            />
            {showSuggestions && symbol && allowedSymbols.length > 0 && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
                background: '#0f172a', border: '1px solid #475569', borderRadius: '8px',
                marginTop: '4px', maxHeight: '200px', overflow: 'auto'
              }}>
                {allowedSymbols
                  .filter(s => s.includes(symbol))
                  .slice(0, 8)
                  .map(s => (
                    <div
                      key={s}
                      onClick={() => { setSymbol(s); setShowSuggestions(false); }}
                      style={{
                        padding: '8px 16px', cursor: 'pointer', fontSize: '14px',
                        color: '#cbd5e1', borderBottom: '1px solid #1e293b'
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = '#1e293b')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      {s}
                    </div>
                  ))}
                {allowedSymbols.filter(s => s.includes(symbol)).length === 0 && (
                  <div style={{ padding: '8px 16px', fontSize: '13px', color: '#ef4444' }}>
                    Not in your Watchlist or Portfolio
                  </div>
                )}
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={loading || !symbol.trim() || (!allowedSymbols.includes(symbol.trim().toUpperCase()) && !allowedLoading)}
            style={{
              padding: '10px 24px', borderRadius: '8px', border: 'none',
              background: loading ? '#475569' : (!symbol.trim() || (!allowedSymbols.includes(symbol.trim().toUpperCase()) && !allowedLoading)) ? '#334155' : '#8b5cf6',
              color: '#fff', fontWeight: 600, cursor: loading ? 'not-allowed' : (!symbol.trim() ? 'not-allowed' : 'pointer'),
              whiteSpace: 'nowrap'
            }}
          >
            {loading ? 'Scanning…' : 'Run Unified Scan'}
          </button>
        </form>
        {symbol && !allowedLoading && !allowedSymbols.includes(symbol.trim().toUpperCase()) && (
          <div style={{ marginTop: '8px', fontSize: '12px', color: '#ef4444' }}>
            ⚠ {symbol.trim().toUpperCase()} is not in your Watchlist or Portfolio. Add it first.
          </div>
        )}
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: '#450a0a', border: '1px solid #991b1b', borderRadius: '8px', color: '#fca5a5', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {loading && (
        <div style={{
          padding: '48px 24px', background: '#1e293b', borderRadius: '12px',
          border: '1px solid #334155', textAlign: 'center', marginBottom: '24px'
        }}>
          <div style={{ fontSize: '40px', marginBottom: '16px', animation: 'pulse 1.5s ease-in-out infinite' }}>
            🧠
          </div>
          <div style={{ fontSize: '18px', fontWeight: 600, color: '#f1f5f9', marginBottom: '8px' }}>
            Running Unified Institutional Scan
          </div>
          <div style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '24px' }}>
            Composing PERX re-rating analysis, AAE forensic layers,<br />
            GuidanceCheck credibility, and MOSI multi-bagger scoring…
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
            {['PERX', 'AAE', 'Guidance', 'MOSI'].map((engine) => (
              <div key={engine} style={{
                padding: '8px 16px', borderRadius: '6px',
                background: '#0f172a', border: '1px solid #334155',
                fontSize: '12px', color: '#8b5cf6', fontWeight: 600,
                opacity: 0.6
              }}>
                {engine}
              </div>
            ))}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '16px' }}>
            This may take 10–30 seconds for large-cap stocks with extensive data
          </div>
        </div>
      )}

      {result && (
        <>
          {/* Signal Card */}
          <div style={{
            padding: '24px', borderRadius: '12px', marginBottom: '20px',
            background: `linear-gradient(135deg, ${getRatingColor(result.signal?.rating)}22, #1e293b)`,
            border: `2px solid ${getRatingColor(result.signal?.rating)}44`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '4px' }}>MOSI Multi-Bagger Signal</div>
                <div style={{ fontSize: '36px', fontWeight: 700, color: getRatingColor(result.signal?.rating) }}>
                  {result.signal?.rating || '—'}
                </div>
                <div style={{ fontSize: '14px', color: '#94a3b8', marginTop: '4px' }}>
                  {result.symbol} • {result.perx?.header?.lifecycle_phase || result.perx?.lifecycle?.stage || ''}
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '4px' }}>Multi-Bagger Probability</div>
                <div style={{ fontSize: '48px', fontWeight: 800, color: '#f1f5f9' }}>
                  {result.signal?.probability_score?.toFixed(1) || '—'}<span style={{ fontSize: '20px', color: '#64748b' }}>/10</span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ display: 'flex', gap: '12px' }}>
                  {result.perx?.header?.perx_score !== undefined && (
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>PERX</div>
                      <div style={{ fontSize: '28px', fontWeight: 700, color: '#2563eb' }}>{result.perx.header.perx_score}</div>
                    </div>
                  )}
                  {result.aae?.master_score !== undefined && (
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>AAE</div>
                      <div style={{ fontSize: '28px', fontWeight: 700, color: '#8b5cf6' }}>{result.aae.master_score}</div>
                    </div>
                  )}
                  {result.guidance?.accuracy_pct !== undefined && result.guidance?.total_promises > 0 && (
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>Credibility</div>
                      <div style={{ fontSize: '28px', fontWeight: 700, color: '#22c55e' }}>{result.guidance.accuracy_pct}%</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '16px', borderBottom: '1px solid #334155', paddingBottom: '12px' }}>
            {(['overview', 'perx', 'aae', 'guidance', 'mosi'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  padding: '8px 16px', borderRadius: '6px', border: 'none',
                  background: tab === t ? '#334155' : 'transparent',
                  color: tab === t ? '#f1f5f9' : '#94a3b8',
                  cursor: 'pointer', fontSize: '13px', fontWeight: tab === t ? 600 : 400,
                  textTransform: 'capitalize'
                }}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {tab === 'overview' && <OverviewTab result={result} />}
          {tab === 'perx' && <PerxTab result={result} />}
          {tab === 'aae' && <AaeTab result={result} />}
          {tab === 'guidance' && <GuidanceTab result={result} />}
          {tab === 'mosi' && <MosiTab result={result} />}

          {/* Warnings */}
          {result._warnings?.length > 0 && (
            <div style={{ marginTop: '20px', padding: '12px 16px', background: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '8px' }}>Data Warnings</div>
              {result._warnings.map((w: string, i: number) => (
                <div key={i} style={{ fontSize: '12px', color: '#eab308', marginBottom: '4px' }}>⚠ {w}</div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ─── Tab Components ─────────────────────────────────────── */

function OverviewTab({ result }: { result: any }) {
  const sig = result.signal || {};
  const breakdown = sig.breakdown || {};
  const dims = [
    { key: 'revenue_growth', label: 'Revenue Growth', max: '1.5' },
    { key: 'margin_expansion', label: 'Margin Expansion', max: '1.5' },
    { key: 'roce_quality', label: 'ROCE Quality', max: '1.5' },
    { key: 'tam_headroom', label: 'TAM Headroom', max: '1.5' },
    { key: 'balance_sheet', label: 'Balance Sheet', max: '1.0' },
    { key: 'narrative_confirmation', label: 'Narrative', max: '1.0' },
    { key: 'stage_cycle', label: 'Stage Cycle', max: '1.0' },
  ];

  return (
    <div style={{ display: 'grid', gap: '16px' }}>
      {/* Multi-Bagger Breakdown */}
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '15px', color: '#f1f5f9' }}>Multi-Bagger Score Breakdown</h3>
        <div style={{ display: 'grid', gap: '8px' }}>
          {dims.map(d => {
            const bd = breakdown[d.key] || {};
            const score = bd.score ?? 0;
            const full = parseFloat(d.max);
            const pct = full > 0 ? (score / full) * 100 : 0;
            return (
              <div key={d.key}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '13px', color: '#cbd5e1' }}>{d.label}</span>
                  <span style={{ fontSize: '13px', color: '#94a3b8' }}>{score}/{d.max}</span>
                </div>
                <div style={{ height: '6px', background: '#334155', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: pct >= 80 ? '#22c55e' : pct >= 50 ? '#eab308' : '#ef4444', borderRadius: '3px', transition: 'width 0.3s' }} />
                </div>
                <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>{bd.reason}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Executive Summary */}
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 8px 0', fontSize: '15px', color: '#f1f5f9' }}>Executive Summary</h3>
        <p style={{ fontSize: '14px', color: '#cbd5e1', lineHeight: 1.6 }}>
          {result.perx?.executive_summary || result.perx?.final_institutional_verdict || 'No summary available.'}
        </p>
      </div>
    </div>
  );
}

function PerxTab({ result }: { result: any }) {
  const perx = result.perx || {};
  const engine = perx.engine_outputs || {};
  const inv = perx.investor_context || {};
  const mri = engine.mri || {};
  const valuation = inv.valuation || {};

  return (
    <div style={{ display: 'grid', gap: '16px' }}>
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>PERX Score & Lifecycle</h3>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          <div><span style={{ color: '#94a3b8', fontSize: '13px' }}>Score</span><div style={{ fontSize: '32px', fontWeight: 700, color: '#2563eb' }}>{perx.header?.perx_score || perx.score || '—'}</div></div>
          <div><span style={{ color: '#94a3b8', fontSize: '13px' }}>Lifecycle</span><div style={{ fontSize: '18px', fontWeight: 600, color: '#8b5cf6' }}>{perx.header?.lifecycle_phase || perx.lifecycle?.stage || '—'}</div></div>
          <div><span style={{ color: '#94a3b8', fontSize: '13px' }}>Narrative Intensity</span><div style={{ fontSize: '18px', fontWeight: 600, color: '#f1f5f9' }}>{engine.perx?.narrative_intensity || perx.lifecycle?.narrative_intensity || '—'}</div></div>
          <div><span style={{ color: '#94a3b8', fontSize: '13px' }}>Regime</span><div style={{ fontSize: '18px', fontWeight: 600, color: '#22c55e' }}>{engine.perx?.market_regime || '—'}</div></div>
        </div>
      </div>

      {/* MRI Breakdown */}
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>MRI Technical (7-Step)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px,1fr))', gap: '8px' }}>
          {Object.entries(mri).filter(([k]) => k !== 'volume_multiple_20d').map(([k, v]) => (
            <div key={k} style={{ padding: '8px 12px', background: '#0f172a', borderRadius: '6px' }}>
              <span style={{ fontSize: '11px', color: '#64748b', display: 'block' }}>{k.replace(/_/g, ' ')}</span>
              <span style={{ fontSize: '13px', color: String(v) === 'Strong' || String(v) === 'Bullish' || String(v) === 'Active' || String(v) === 'Confirmed' ? '#22c55e' : '#94a3b8' }}>{String(v)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Valuation */}
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>Valuation Context</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px,1fr))', gap: '8px' }}>
          <KV label="P/E" value={valuation.pe_ratio} suffix="x" />
          <KV label="Sector Median P/E" value={valuation.sector_median_pe} suffix="x" />
          <KV label="P/E Percentile" value={valuation.pe_percentile_vs_history} suffix="th" />
          <KV label="PEG" value={inv.peg_ratio?.peg_ratio} suffix="x" />
          <KV label="EV/EBITDA" value={inv.ev_ebitda?.ev_ebitda} suffix="x" />
          <KV label="P/S" value={inv.ps_ratio?.ps_ratio} suffix="x" />
        </div>
        <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>{valuation.verdict}</div>
      </div>
    </div>
  );
}

function AaeTab({ result }: { result: any }) {
  const aae = result.aae || {};
  const layers = aae.layers || {};

  return (
    <div style={{ display: 'grid', gap: '16px' }}>
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>AAE Master Score</h3>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ fontSize: '48px', fontWeight: 800, color: '#8b5cf6' }}>{aae.master_score || aae.error ? aae.master_score || '—' : '—'}</div>
          <div>
            <div style={{ fontSize: '13px', color: '#94a3b8' }}>Status: <span style={{ color: aae.status === 'ACTIVE' ? '#22c55e' : '#ef4444' }}>{aae.status || '—'}</span></div>
            <div style={{ fontSize: '13px', color: '#94a3b8' }}>Sector: {aae.sector || '—'}</div>
            <div style={{ fontSize: '13px', color: '#94a3b8' }}>Market Confirmation: {aae.market_confirmation || '—'}</div>
          </div>
        </div>
      </div>

      {layers && Object.keys(layers).length > 0 && (
        <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>10-Layer Forensic Breakdown</h3>
          <div style={{ display: 'grid', gap: '6px' }}>
            {Object.entries(layers).map(([k, v]: [string, any]) => {
              if (typeof v !== 'object' || !v) return null;
              const score = v.score ?? v.master_score ?? (v.summary ? 50 : null);
              return (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 12px', background: '#0f172a', borderRadius: '6px' }}>
                  <span style={{ fontSize: '13px', color: '#cbd5e1', textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                    {score !== null ? `${score}/100` : String(v.summary || v.source || '').slice(0, 50)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Bear/Bull Debate */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        {aae.bull_case && (
          <div style={{ padding: '16px', background: '#052e16', borderRadius: '12px', border: '1px solid #166534' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#22c55e' }}>🐂 Bull Case</h4>
            <div style={{ fontSize: '12px', color: '#86efac', lineHeight: 1.5 }}>{typeof aae.bull_case === 'string' ? aae.bull_case.slice(0, 300) : JSON.stringify(aae.bull_case).slice(0, 300)}</div>
          </div>
        )}
        {aae.bear_case && (
          <div style={{ padding: '16px', background: '#450a0a', borderRadius: '12px', border: '1px solid #991b1b' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#ef4444' }}>🐻 Bear Case</h4>
            <div style={{ fontSize: '12px', color: '#fca5a5', lineHeight: 1.5 }}>{typeof aae.bear_case === 'string' ? aae.bear_case.slice(0, 300) : JSON.stringify(aae.bear_case).slice(0, 300)}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function GuidanceTab({ result }: { result: any }) {
  const g = result.guidance || {};
  if (g.error) return <Panel title="Management Credibility"><p style={{ color: '#94a3b8' }}>No credibility data available yet. Guidance auto-priming runs in background when stocks are added.</p></Panel>;
  if (!g.total_promises || g.total_promises === 0) return <Panel title="Management Credibility"><p style={{ color: '#94a3b8' }}>No verifiable management promises found yet. Needs more quarterly data after guidance statements are extracted from concall transcripts.</p></Panel>;

  return (
    <div style={{ display: 'grid', gap: '16px' }}>
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>Management Credibility</h3>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          <div><span style={{ color: '#94a3b8', fontSize: '13px' }}>Accuracy</span><div style={{ fontSize: '36px', fontWeight: 700, color: g.accuracy_pct >= 70 ? '#22c55e' : g.accuracy_pct >= 50 ? '#eab308' : '#ef4444' }}>{g.accuracy_pct}%</div></div>
          <div><span style={{ color: '#94a3b8', fontSize: '13px' }}>Trend</span><div style={{ fontSize: '20px', fontWeight: 600, color: g.trend === 'IMPROVING' ? '#22c55e' : g.trend === 'DETERIORATING' ? '#ef4444' : '#eab308' }}>{g.trend}</div></div>
          <div><span style={{ color: '#94a3b8', fontSize: '13px' }}>Achieved</span><div style={{ fontSize: '20px', fontWeight: 600, color: '#f1f5f9' }}>{g.achieved}/{g.total_promises}</div></div>
          <div><span style={{ color: '#94a3b8', fontSize: '13px' }}>Missed</span><div style={{ fontSize: '20px', fontWeight: 600, color: '#ef4444' }}>{g.missed}</div></div>
        </div>
      </div>
    </div>
  );
}

function MosiTab({ result }: { result: any }) {
  const mosi = result.mosi_additions || {};
  const qt = mosi.quarterly_table || {};
  const peers = mosi.peer_fundamentals || {};
  const ps = mosi.ps_ratio || {};

  return (
    <div style={{ display: 'grid', gap: '16px' }}>
      {/* P/S Ratio */}
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 8px 0', fontSize: '15px', color: '#f1f5f9' }}>P/S Ratio (Price-to-Sales)</h3>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          <KV label="P/S" value={ps.ps_ratio} suffix="x" />
          <KV label="TTM Revenue" value={ps.ttm_revenue_cr} suffix="Cr" />
        </div>
        <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>{ps.verdict}</div>
        {ps.homework && <div style={{ fontSize: '11px', color: '#8b5cf6', marginTop: '4px' }}>📋 {ps.homework}</div>}
      </div>

      {/* Quarterly Table */}
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155', overflow: 'auto' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>6-Quarter Performance Table</h3>
        <div style={{ fontSize: '13px', color: qt.verdict?.startsWith('ACCELERATING') ? '#22c55e' : qt.verdict?.startsWith('DECELERATING') ? '#ef4444' : '#eab308', marginBottom: '12px' }}>{qt.verdict}</div>
        {qt.quarters?.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155' }}>
                <th style={{ padding: '8px', textAlign: 'left', color: '#94a3b8' }}>Quarter</th>
                <th style={{ padding: '8px', textAlign: 'right', color: '#94a3b8' }}>Rev (Cr)</th>
                <th style={{ padding: '8px', textAlign: 'right', color: '#94a3b8' }}>Rev YoY%</th>
                <th style={{ padding: '8px', textAlign: 'right', color: '#94a3b8' }}>EBITDA (Cr)</th>
                <th style={{ padding: '8px', textAlign: 'right', color: '#94a3b8' }}>EBITDA YoY%</th>
                <th style={{ padding: '8px', textAlign: 'right', color: '#94a3b8' }}>PAT (Cr)</th>
                <th style={{ padding: '8px', textAlign: 'right', color: '#94a3b8' }}>PAT YoY%</th>
                <th style={{ padding: '8px', textAlign: 'center', color: '#94a3b8' }}>Accel</th>
              </tr>
            </thead>
            <tbody>
              {qt.quarters.map((q: any, i: number) => (
                <tr key={i} style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '8px', color: '#cbd5e1' }}>{q.quarter}</td>
                  <td style={{ padding: '8px', textAlign: 'right', color: '#f1f5f9' }}>{q.revenue_cr?.toLocaleString() || '—'}</td>
                  <td style={{ padding: '8px', textAlign: 'right', color: q.rev_yoy_pct >= 20 ? '#22c55e' : q.rev_yoy_pct >= 0 ? '#eab308' : '#ef4444' }}>{q.rev_yoy_pct != null ? `${q.rev_yoy_pct}%` : '—'}</td>
                  <td style={{ padding: '8px', textAlign: 'right', color: '#f1f5f9' }}>{q.ebitda_cr?.toLocaleString() || '—'}</td>
                  <td style={{ padding: '8px', textAlign: 'right', color: q.ebitda_yoy_pct >= 20 ? '#22c55e' : q.ebitda_yoy_pct >= 0 ? '#eab308' : '#ef4444' }}>{q.ebitda_yoy_pct != null ? `${q.ebitda_yoy_pct}%` : '—'}</td>
                  <td style={{ padding: '8px', textAlign: 'right', color: '#f1f5f9' }}>{q.pat_cr?.toLocaleString() || '—'}</td>
                  <td style={{ padding: '8px', textAlign: 'right', color: q.pat_yoy_pct >= 20 ? '#22c55e' : q.pat_yoy_pct >= 0 ? '#eab308' : '#ef4444' }}>{q.pat_yoy_pct != null ? `${q.pat_yoy_pct}%` : '—'}</td>
                  <td style={{ padding: '8px', textAlign: 'center', fontSize: '16px' }}>{q.accel_flag}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p style={{ color: '#94a3b8', fontSize: '13px' }}>No quarterly data available.</p>}
      </div>

      {/* Peer Comparison */}
      <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>Peer Fundamental Comparison</h3>
        <div style={{ fontSize: '13px', color: '#cbd5e1', marginBottom: '12px' }}>{peers.verdict}</div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <KV label="Self OPM" value={peers.self_opm} suffix="%" />
          <KV label="Self ROCE" value={peers.self_roce} suffix="%" />
          <KV label="Self Rev CAGR" value={peers.self_revenue_cagr} suffix="%" />
          {peers.sector_medians && (
            <>
              <KV label="Sector OPM" value={peers.sector_medians?.opm} suffix="%" />
              <KV label="Sector ROCE" value={peers.sector_medians?.roce} suffix="%" />
              <KV label="Sector CAGR" value={peers.sector_medians?.revenue_cagr} suffix="%" />
            </>
          )}
        </div>
        {peers.peers?.length > 0 && (
          <div>
            <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px' }}>Top Peers</div>
            {peers.peers.map((p: any, i: number) => (
              <div key={i} style={{ display: 'flex', gap: '12px', padding: '4px 0', fontSize: '12px', color: '#94a3b8' }}>
                <span style={{ width: '80px', color: '#cbd5e1' }}>{p.symbol}</span>
                <span>OPM: {p.opm || '—'}%</span>
                <span>ROCE: {p.roce || '—'}%</span>
                <span>CAGR: {p.revenue_cagr || '—'}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Reusable Components ─────────────────────────────────── */

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: '20px', background: '#1e293b', borderRadius: '12px', border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#f1f5f9' }}>{title}</h3>
      {children}
    </div>
  );
}

function KV({ label, value, suffix }: { label: string; value: any; suffix?: string }) {
  return (
    <div style={{ padding: '8px 12px', background: '#0f172a', borderRadius: '6px', minWidth: '120px' }}>
      <span style={{ fontSize: '11px', color: '#64748b', display: 'block' }}>{label}</span>
      <span style={{ fontSize: '16px', color: '#f1f5f9', fontWeight: 600 }}>
        {value != null ? `${value}${suffix || ''}` : '—'}
      </span>
    </div>
  );
}
