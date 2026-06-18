import { useEffect, useState } from 'react';
import { apiFetch } from './api';

// ── Types ────────────────────────────────────────────────────────────

interface Header {
  symbol: string;
  company_name: string;
  sector: string | null;
  pe_score: number;
  rank: number | null;
  total: number | null;
  bucket: string;
  generated_at_iso: string;
  generated_at_ist: string;
}

interface Coverage {
  n_promises_total: number;
  n_quote_verified: number;
  n_transcripts: number;
  n_quarter_span: number;
}

interface CategoryRow {
  code: string;
  label: string;
  weight: number;
  signal_strength: number;
  contribution: number;
  sources: string[];
  missing: boolean;
}

interface PrimaryRow {
  guidance_type: string;
  current_status: string;
  current_quarter: string;
  first_seen_quarter: string;
  target_value: number | null;
  target_unit: string | null;
  target_date: string | null;
  guidance_text: string;
  current_evidence_quote: string | null;
  quote_verified: boolean;
}

interface SecondaryRow {
  category_code: string;
  label: string;
  mentions: number;
  transcripts_with_hits: number;
  has_execution: boolean;
  signal_strength: number;
  snippets: string[];
}

interface Totals {
  raw_score: number;
  max_possible: number;
  scaled_percent: number;
}

interface PeReport {
  header: Header;
  coverage: Coverage;
  category_breakdown: CategoryRow[];
  top_drivers: string[];
  primary_detail: PrimaryRow[];
  secondary_detail: SecondaryRow[];
  totals: Totals;
}

// ── Style helpers ────────────────────────────────────────────────────

const colors = {
  bg: '#020617',
  panel: '#0f172a',
  panel2: '#1e293b',
  border: '#334155',
  text: '#f1f5f9',
  textDim: '#94a3b8',
  textMuted: '#64748b',
  accent: '#3b82f6',
  strong: '#22c55e',
  warn: '#f59e0b',
  bad: '#ef4444',
};

const bucketColor = (b: string) => ({
  Strong: colors.strong,
  Moderate: colors.accent,
  Watch: colors.warn,
  Weak: colors.bad,
  Negligible: colors.textMuted,
}[b] || colors.textMuted);

const strengthBar = (n: number) => '█'.repeat(Math.max(0, Math.min(5, n))) + '░'.repeat(5 - Math.max(0, Math.min(5, n)));
const strengthColor = (n: number) =>
  n >= 4 ? colors.strong : n >= 3 ? colors.accent : colors.textMuted;

const statusColor = (s: string) => ({
  FULFILLED: colors.strong, REVISED_UP: colors.strong, ON_TRACK: colors.accent,
  PARTIALLY_FULFILLED: colors.warn, PENDING: colors.textMuted, NEW: colors.textMuted,
  REVISED_DOWN: colors.bad, MISSED: colors.bad,
}[s] || colors.textMuted);

// ── Component ────────────────────────────────────────────────────────

export default function PeExpansionReport({ symbol: propSymbol, onBack }: { symbol: string; onBack?: () => void }) {
  const [symbol, setSymbol] = useState((propSymbol || '').toUpperCase());
  const [report, setReport] = useState<PeReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailStatus, setEmailStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [emailMsg, setEmailMsg] = useState<string>('');
  const [recipient, setRecipient] = useState('');

  // Search + Top 10 state (manual-refresh, 149-universe scope)
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{symbol: string; company_name: string; pe_score: number | null}>>([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [top10, setTop10] = useState<{as_of: string | null; total_in_universe: number; results: any[]} | null>(null);

  // Fetch top 10 once on mount
  useEffect(() => {
    apiFetch('/pe-expansion/top10')
      .then((r: any) => setTop10(r))
      .catch(() => setTop10(null));
  }, []);

  // Debounced search
  useEffect(() => {
    if (searchQ.trim().length === 0) {
      setSearchResults([]);
      return;
    }
    const t = setTimeout(() => {
      apiFetch(`/pe-expansion/suggest?q=${encodeURIComponent(searchQ.trim())}&limit=8`)
        .then((r: any) => setSearchResults(r.results || []))
        .catch(() => setSearchResults([]));
    }, 200);
    return () => clearTimeout(t);
  }, [searchQ]);

  // Fetch report when symbol changes
  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    setShowSearchDropdown(false);
    setSearchQ('');
    apiFetch(`/pe-expansion/${encodeURIComponent(symbol)}`)
      .then((r: PeReport) => setReport(r))
      .catch((e: any) => setError(typeof e === 'string' ? e : JSON.stringify(e)))
      .finally(() => setLoading(false));
  }, [symbol]);

  const sendEmail = async () => {
    if (!recipient || !recipient.includes('@')) {
      setEmailMsg('Enter a valid email');
      setEmailStatus('error');
      return;
    }
    setEmailStatus('sending');
    setEmailMsg('');
    try {
      const r = await apiFetch(`/pe-expansion/email/${encodeURIComponent(symbol!.toUpperCase())}?to=${encodeURIComponent(recipient)}`, { method: 'POST' });
      setEmailStatus('sent');
      setEmailMsg(r.status === 'sent' ? `Sent (message ${r.message_id?.slice(0,12)}…)` : `Dev-logged to ${r.dev_path}`);
    } catch (e: any) {
      setEmailStatus('error');
      setEmailMsg(typeof e === 'string' ? e : JSON.stringify(e));
    }
  };

  const h = report?.header;
  const bucketC = h ? bucketColor(h.bucket) : colors.textMuted;
  const lastPromiseQuarter = (() => {
    if (!report || !report.primary_detail) return null;
    const quarters = report.primary_detail.map(p => p.first_seen_quarter).filter(Boolean) as string[];
    if (quarters.length === 0) return null;
    return quarters.sort().reverse()[0];
  })();
  const asOfIstLabel = top10?.as_of ? new Date(top10.as_of).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' }) : '—';

  return (
    <div style={{ background: colors.bg, minHeight: '100vh', color: colors.text, fontFamily: '-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        {/* ── Search + Top 10 panel (always visible) ── */}
        <div style={{ padding: '24px 40px', background: colors.panel, borderBottom: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 12 }}>
            🔍 Search 149-symbol universe
          </div>
          <div style={{ position: 'relative', marginBottom: 20 }}>
            <input
              type="text"
              value={searchQ}
              onChange={e => { setSearchQ(e.target.value); setShowSearchDropdown(true); }}
              onFocus={() => setShowSearchDropdown(true)}
              onBlur={() => setTimeout(() => setShowSearchDropdown(false), 200)}
              placeholder="Symbol or company name…"
              style={{ width: '100%', padding: '10px 14px', background: colors.panel2, color: colors.text, border: `1px solid ${colors.border}`, borderRadius: 6, fontSize: 14, outline: 'none', boxSizing: 'border-box' }}
            />
            {showSearchDropdown && searchResults.length > 0 && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: colors.panel2, border: `1px solid ${colors.border}`, borderRadius: 6, marginTop: 4, zIndex: 10, maxHeight: 320, overflowY: 'auto' }}>
                {searchResults.map(r => (
                  <div
                    key={r.symbol}
                    onMouseDown={() => { setSymbol(r.symbol); setShowSearchDropdown(false); }}
                    style={{ padding: '10px 14px', borderBottom: `1px solid ${colors.border}`, cursor: 'pointer', fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                  >
                    <div>
                      <span style={{ fontWeight: 700, marginRight: 12, color: colors.text }}>{r.symbol}</span>
                      <span style={{ color: colors.textDim }}>{r.company_name}</span>
                    </div>
                    {r.pe_score !== null && r.pe_score !== undefined && (
                      <span style={{ color: r.pe_score >= 80 ? colors.strong : r.pe_score >= 65 ? colors.accent : colors.textMuted, fontWeight: 700 }}>
                        {r.pe_score.toFixed(1)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {top10 && (
            <>
              <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 8 }}>
                Top 10 · {top10.total_in_universe} symbols in universe
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 4 }}>
                {top10.results.map(r => (
                  <div
                    key={r.symbol}
                    onClick={() => setSymbol(r.symbol)}
                    style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: colors.panel2, borderRadius: 4, cursor: 'pointer', fontSize: 12, alignItems: 'center' }}
                  >
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ color: colors.textMuted, marginRight: 8 }}>#{r.rank}</span>
                      <span style={{ fontWeight: 700, marginRight: 8, color: colors.text }}>{r.symbol}</span>
                      <span style={{ color: colors.textDim }}>{r.company_name}</span>
                    </div>
                    <span style={{ color: (r.pe_score ?? 0) >= 80 ? colors.strong : (r.pe_score ?? 0) >= 65 ? colors.accent : colors.textMuted, fontWeight: 700, marginLeft: 8 }}>
                      {typeof r.pe_score === 'number' ? r.pe_score.toFixed(1) : r.pe_score}
                    </span>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 11, color: colors.textMuted, marginTop: 12, lineHeight: 1.6 }}>
                Last persist: {asOfIstLabel} IST ·{' '}
                To refresh: <code style={{ background: colors.panel2, padding: '1px 6px', borderRadius: 3, color: colors.text }}>python -m engine_perx.pe_signals --persist</code>
              </div>
            </>
          )}
        </div>

        {/* ── Loading / Error states ── */}
        {loading && (
          <div style={{ padding: 60, color: colors.textDim, fontSize: 14, textAlign: 'center' }}>
            Loading Expansion Lens report for <span style={{ color: colors.text, fontWeight: 700 }}>{symbol}</span>…
          </div>
        )}
        {error && !loading && (
          <div style={{ padding: 60, color: colors.bad, fontSize: 14, textAlign: 'center' }}>
            Error loading {symbol}: {error}
          </div>
        )}

        {/* ── Report sections (only when loaded) ── */}
        {report && !loading && !error && (() => {
          const h = report.header;
          const cov = report.coverage;
          return (
        <>
        {/* ── Header ── */}
        <div style={{ padding: '32px 40px', background: colors.panel, borderBottom: `3px solid ${bucketC}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 6 }}>
                MRI · Expansion Lens
              </div>
              <div style={{ fontSize: 32, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>{h.company_name}</div>
              <div style={{ fontSize: 13, color: colors.textDim, marginBottom: 4 }}>
                {h.sector || '—'} · {h.symbol} · {h.generated_at_ist}
              </div>
              <div style={{ fontSize: 11, color: colors.textMuted, marginBottom: 24, lineHeight: 1.5 }}>
                Data spans {cov.n_quarter_span} quarter{cov.n_quarter_span === 1 ? '' : 's'}
                {lastPromiseQuarter ? ` · latest promise ${lastPromiseQuarter}` : ''}
                {' · '}Manual refresh only — last persisted {asOfIstLabel} IST
              </div>
            </div>
            {onBack && (
              <button
                onClick={onBack}
                style={{
                  padding: '8px 16px', background: colors.panel2, color: colors.textDim,
                  border: `1px solid ${colors.border}`, borderRadius: 6, fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                ← Back
              </button>
            )}
          </div>
          <div style={{ display: 'flex', gap: 40, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>PE Score</div>
              <div style={{ fontSize: 56, fontWeight: 800, color: bucketC, lineHeight: 1, marginTop: 4 }}>
                {h.pe_score}<span style={{ fontSize: 18, color: '#475569', fontWeight: 400 }}>/100</span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Universe Rank</div>
              <div style={{ fontSize: 28, fontWeight: 700, marginTop: 8 }}>
                #{h.rank} <span style={{ fontSize: 14, color: colors.textMuted, fontWeight: 400 }}>of {h.total}</span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Classification</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: bucketC, marginTop: 14 }}>{h.bucket}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Coverage</div>
              <div style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.5, marginTop: 10 }}>
                {cov.n_promises_total} promises ({cov.n_quote_verified} verified)<br />
                {cov.n_transcripts} transcripts · {cov.n_quarter_span} quarters
              </div>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <div style={{ fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: 6 }}>Email this report</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  type="email"
                  placeholder="recipient@example.com"
                  value={recipient}
                  onChange={e => setRecipient(e.target.value)}
                  style={{
                    padding: '8px 12px', background: colors.panel2, color: colors.text,
                    border: `1px solid ${colors.border}`, borderRadius: 6, fontSize: 13, minWidth: 220,
                  }}
                />
                <button
                  onClick={sendEmail}
                  disabled={emailStatus === 'sending'}
                  style={{
                    padding: '8px 16px', background: colors.accent, color: 'white',
                    border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600,
                    cursor: emailStatus === 'sending' ? 'wait' : 'pointer',
                    opacity: emailStatus === 'sending' ? 0.6 : 1,
                  }}
                >
                  {emailStatus === 'sending' ? 'Sending…' : 'Send'}
                </button>
              </div>
              {emailMsg && (
                <div style={{ marginTop: 8, fontSize: 12, color: emailStatus === 'error' ? colors.bad : colors.strong }}>
                  {emailMsg}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Top Drivers ── */}
        <div style={{ padding: '20px 40px', background: colors.panel2, borderBottom: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: 10 }}>Top PE Expansion Drivers</div>
          <div style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.7 }}>
            {h.symbol ? null : null}
            {report.top_drivers.slice(0, 5).map((d, i) => (
              <span key={d}><span style={{ color: colors.accent }}>{i+1}.</span> {d} &nbsp; </span>
            ))}
          </div>
        </div>

        {/* ── Category Breakdown ── */}
        <div style={{ padding: '32px 40px', background: colors.panel }}>
          <div style={{ fontSize: 14, color: colors.text, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 16 }}>
            Category Breakdown
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, color: '#cbd5e1' }}>
            <thead>
              <tr style={{ background: colors.panel2 }}>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: colors.textDim, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Category</th>
                <th style={{ textAlign: 'center', padding: '10px 12px', color: colors.textDim, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Weight</th>
                <th style={{ textAlign: 'center', padding: '10px 12px', color: colors.textDim, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Strength</th>
                <th style={{ textAlign: 'right', padding: '10px 12px', color: colors.textDim, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Contribution</th>
                <th style={{ textAlign: 'left', padding: '10px 12px', color: colors.textDim, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Sources</th>
              </tr>
            </thead>
            <tbody>
              {report.category_breakdown.map(c => (
                <tr key={c.code}>
                  <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.panel2}`, color: c.missing ? colors.textMuted : colors.text }}>{c.label}</td>
                  <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.panel2}`, textAlign: 'center', color: c.missing ? colors.textMuted : '#cbd5e1', fontWeight: 600 }}>{c.weight}</td>
                  <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.panel2}`, textAlign: 'center', color: c.missing ? '#334155' : strengthColor(c.signal_strength), fontFamily: 'monospace', letterSpacing: '0.1em' }}>
                    {strengthBar(c.signal_strength)}
                  </td>
                  <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.panel2}`, textAlign: 'right', color: c.missing ? colors.textMuted : colors.text, fontWeight: 700 }}>{c.missing ? '—' : c.contribution}</td>
                  <td style={{ padding: '10px 12px', borderBottom: `1px solid ${colors.panel2}` }}>
                    {c.sources.map(s => (
                      <span key={s} style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4, background: s === 'primary' ? '#1e40af' : '#7c2d12', color: colors.text, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', marginRight: 4 }}>{s}</span>
                    ))}
                    {c.missing && <span style={{ color: colors.textMuted, fontStyle: 'italic' }}>no evidence</span>}
                  </td>
                </tr>
              ))}
              <tr>
                <td colSpan={3} style={{ padding: '14px 12px', color: colors.textDim, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Total</td>
                <td style={{ padding: '14px 12px', textAlign: 'right', color: colors.text, fontWeight: 800, fontSize: 15 }}>{report.totals.raw_score} / {report.totals.max_possible}</td>
                <td style={{ padding: '14px 12px', color: bucketC, fontWeight: 700 }}>{report.totals.scaled_percent}%</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* ── Primary Source ── */}
        <div style={{ padding: '32px 40px', background: '#0b1220', borderTop: `1px solid ${colors.panel2}` }}>
          <div style={{ fontSize: 14, color: colors.text, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 6 }}>
            Primary Source — Promise Tracker
          </div>
          <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 16 }}>
            LLM-extracted commitments from management commentary, cross-traced across transcripts.
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, color: '#cbd5e1' }}>
            <thead>
              <tr style={{ background: colors.panel2 }}>
                <th style={{ textAlign: 'left', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Quarter</th>
                <th style={{ textAlign: 'left', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Type</th>
                <th style={{ textAlign: 'left', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Status</th>
                <th style={{ textAlign: 'left', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Target</th>
                <th style={{ textAlign: 'left', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Commitment</th>
              </tr>
            </thead>
            <tbody>
              {report.primary_detail.slice(0, 15).map((p, i) => (
                <tr key={i}>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, color: colors.textDim, fontFamily: 'monospace' }}>{(p.first_seen_quarter || '?').slice(0, 10)}</td>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}` }}>{(p.guidance_type || '?').slice(0, 18)}</td>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, color: statusColor(p.current_status), fontWeight: 600 }}>{(p.current_status || '?').slice(0, 22)}</td>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, fontFamily: 'monospace' }}>
                    {p.target_value !== null ? `${p.target_value}${p.target_unit || ''}` : (p.target_date || '')}
                  </td>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, color: colors.text }}>{(p.guidance_text || '').slice(0, 100)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ── Secondary Source ── */}
        <div style={{ padding: '32px 40px', background: colors.panel, borderTop: `1px solid ${colors.panel2}` }}>
          <div style={{ fontSize: 14, color: colors.text, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 6 }}>
            Secondary Source — Transcript Keyword Scan
          </div>
          <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 16 }}>
            Environmental categories scanned across the full transcript corpus.
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, color: '#cbd5e1' }}>
            <thead>
              <tr style={{ background: colors.panel2 }}>
                <th style={{ textAlign: 'left', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Category</th>
                <th style={{ textAlign: 'right', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Mentions</th>
                <th style={{ textAlign: 'right', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Transcripts</th>
                <th style={{ textAlign: 'center', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Execution?</th>
                <th style={{ textAlign: 'center', padding: '8px 10px', color: colors.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', borderBottom: `1px solid ${colors.border}` }}>Strength</th>
              </tr>
            </thead>
            <tbody>
              {report.secondary_detail.map(s => (
                <tr key={s.category_code}>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, color: colors.text }}>{s.label}</td>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, textAlign: 'right', fontFamily: 'monospace' }}>{s.mentions}</td>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, textAlign: 'right', fontFamily: 'monospace' }}>{s.transcripts_with_hits}</td>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, textAlign: 'center', color: s.has_execution ? colors.strong : colors.textMuted, fontWeight: s.has_execution ? 700 : 400 }}>
                    {s.has_execution ? 'YES' : '—'}
                  </td>
                  <td style={{ padding: '8px 10px', borderBottom: `1px solid ${colors.panel2}`, textAlign: 'center', color: strengthColor(s.signal_strength), fontFamily: 'monospace', letterSpacing: '0.1em' }}>
                    {strengthBar(s.signal_strength)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ── Footer ── */}
        <div style={{ padding: '24px 40px', background: '#020617', borderTop: `1px solid ${colors.panel2}` }}>
          <div style={{ fontSize: 11, color: '#475569', lineHeight: 1.6 }}>
            MRI — Market Regime Intelligence. Decision-support analytics; not SEBI-registered investment advice.
            Generated by the MRI Expansion Lens engine from the {h.symbol} transcript corpus.<br />
            No buy/sell signals. No price targets. No trading calls. PE Score is a relative rerating-probability indicator.
          </div>
          <div style={{ fontSize: 11, color: '#334155', marginTop: 12 }}>
            Report {h.generated_at_iso} · perx_pe_scores v1
          </div>
        </div>
        </>
          );
        })()}

      </div>
    </div>
  );
}
