import { Fragment, ReactNode, useEffect, useMemo, useState } from 'react';
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
  quote?: {
    text: string;
    source: string;
    quarter?: string;
  };
  status_grid?: Array<{
    quarter: string;
    n_promises: number;
    counts: Record<string, number>;
  }>;
}

interface Credibility {
  accuracy_pct: number | null;
  verdict_zone: string | null;
  trend: string | null;
  consecutive_miss_quarters: number;
  lag_score: number | null;
  total_promises: number;
  achieved_count: number;
  missed_count: number;
  summary: string;
}

interface IndependentCheck {
  master_score: number | null;
  sector: string | null;
  reasons: string[];
  updated_at: string | null;
}

interface FinancialQuality {
  score: number | null;
  category: string | null;
  agents: {
    revenue?: number | null;
    margin?: number | null;
    leverage?: number | null;
    wc?: number | null;
    roce?: number | null;
    evolution?: number | null;
    translation?: number | null;
  };
  flags: string[];
  updated_at: string | null;
}

interface PriceAction {
  total_score: number | null;
  breakout_state: string | null;
  conditions: {
    ema_50_200: boolean;
    ema_200_slope: boolean;
    six_m_high: boolean;
    volume: boolean;
    rs: boolean;
    breakout_10d: boolean;
    price_quality: boolean;
  };
  as_of: string | null;
}

interface CrossCheckRow {
  dimension: string;
  pe_view: string;
  indep_view: string;
  fin_view: string;
  price_view: string;
  alignment: 'all_agree' | 'mostly_agree' | 'mixed' | 'split' | 'no_data';
}

interface BottomLine {
  summary: string;
  action: 'positive' | 'watch' | 'cautious' | 'negative' | 'no_data';
  highlights: Array<{
    signal: string;
    status: string;
    status_label: string;
  }>;
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
  credibility: Credibility | null;
  independent_check: IndependentCheck | null;
  financial_quality: FinancialQuality | null;
  price_action: PriceAction | null;
  cross_check: CrossCheckRow[];
  bottom_line: BottomLine | null;
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

const verdictColor = (v: string | null | undefined): string => {
  if (!v) return colors.textMuted;
  const u = v.toUpperCase();
  if (u.includes('ADD')) return colors.strong;
  if (u.includes('HOLD')) return colors.warn;
  if (u.includes('REDUCE')) return '#fb923c';
  if (u.includes('WATCH')) return colors.textMuted;
  if (u.includes('BROKEN') || u.includes('DISTRUST')) return colors.bad;
  return colors.textMuted;
};

const trendColor = (t: string | null | undefined): string => {
  if (!t) return colors.textMuted;
  const u = t.toUpperCase();
  if (u === 'IMPROVING') return colors.strong;
  if (u === 'DETERIORATING') return colors.bad;
  return colors.textMuted;
};

const scoreVerdict = (s: number | null | undefined): { label: string; color: string } => {
  if (s === null || s === undefined) return { label: 'No data', color: colors.textMuted };
  if (s >= 80) return { label: 'Strong', color: colors.strong };
  if (s >= 60) return { label: 'Holding up', color: colors.accent };
  if (s >= 40) return { label: 'Mixed', color: colors.warn };
  return { label: 'Weak', color: colors.bad };
};

const alignmentLabel: Record<string, { label: string; color: string }> = {
  all_agree:    { label: 'All agree',         color: '#22c55e' },
  mostly_agree: { label: 'Mostly agree',      color: '#3b82f6' },
  mixed:        { label: 'Mixed signals',     color: '#f59e0b' },
  split:        { label: 'Split',             color: '#ef4444' },
  no_data:      { label: 'No data',           color: '#64748b' },
};

// ── Component ────────────────────────────────────────────────────────

export default function PeExpansionReport({ symbol: propSymbol, onBack }: { symbol: string; onBack?: () => void }) {
  const [symbol, setSymbol] = useState((propSymbol || '').toUpperCase());
  const [report, setReport] = useState<PeReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailStatus, setEmailStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [emailMsg, setEmailMsg] = useState<string>('');
  const [recipient, setRecipient] = useState('');

  // Universe (all 149 symbols) state — fetched once on mount
  const [universe, setUniverse] = useState<Array<{symbol: string; company_name: string; pe_score: number | null}>>([]);
  const [universeLoading, setUniverseLoading] = useState(true);
  const [universeError, setUniverseError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');

  // Fetch full universe once on mount
  useEffect(() => {
    apiFetch('/pe-expansion/suggest?q=&limit=200')
      .then((r: any) => {
        // Defensive: only set if response shape matches expectations
        const list = Array.isArray(r?.results) ? r.results : [];
        setUniverse(list.filter((x: any) => x && typeof x.symbol === 'string'));
      })
      .catch((e: any) => setUniverseError(typeof e === 'string' ? e : (e?.message || 'Failed to load universe')))
      .finally(() => setUniverseLoading(false));
  }, []);

  // Client-side filter (no API roundtrip)
  const filteredUniverse = useMemo(() => {
    const q = filter.trim().toUpperCase();
    if (!q) return universe;
    return universe.filter(r =>
      r.symbol.toUpperCase().includes(q) ||
      (r.company_name || '').toUpperCase().includes(q)
    );
  }, [universe, filter]);

  // Fetch report when symbol changes
  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
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
  // /suggest doesn't return as_of, so the refresh timestamp is shown only via
  // the CLI command hint in the universe-list panel footer.

  return (
    <div style={{ background: colors.bg, minHeight: '100vh', color: colors.text, fontFamily: '-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        {/* ── Universe list panel (always visible) ── */}
        <div style={{ padding: '24px 40px', background: colors.panel, borderBottom: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 12 }}>
            📈 Expansion Lens · {universe.length > 0 ? universe.length : '—'}-symbol universe · click any row to load its report
          </div>
          <div style={{ marginBottom: 12 }}>
            <input
              type="text"
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="Filter by symbol or company name…"
              style={{ width: '100%', padding: '10px 14px', background: colors.panel2, color: colors.text, border: `1px solid ${colors.border}`, borderRadius: 6, fontSize: 13, outline: 'none', boxSizing: 'border-box' }}
            />
          </div>

          {universeError && (
            <div style={{ padding: 12, color: colors.bad, fontSize: 13 }}>
              Failed to load universe: {universeError}
            </div>
          )}

          {universeLoading && (
            <div style={{ padding: 12, color: colors.textMuted, fontSize: 13 }}>Loading universe…</div>
          )}

          {!universeLoading && !universeError && filteredUniverse.length === 0 && (
            <div style={{ padding: 12, color: colors.textMuted, fontSize: 13 }}>
              {filter ? `No symbols match "${filter}".` : 'Universe is empty.'}
            </div>
          )}

          {!universeLoading && !universeError && filteredUniverse.length > 0 && (
            <div style={{ maxHeight: 480, overflowY: 'auto', border: `1px solid ${colors.border}`, borderRadius: 6, background: colors.panel2 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead style={{ position: 'sticky', top: 0, background: colors.panel2, zIndex: 1 }}>
                  <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
                    <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.textMuted, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Symbol</th>
                    <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.textMuted, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Company</th>
                    <th style={{ textAlign: 'right', padding: '8px 12px', color: colors.textMuted, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em' }}>PE Score</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUniverse.map(r => {
                    const score = typeof r.pe_score === 'number' ? r.pe_score : null;
                    const scoreColor = score === null ? colors.textMuted : score >= 80 ? colors.strong : score >= 65 ? colors.accent : colors.textMuted;
                    return (
                      <tr
                        key={r.symbol}
                        onClick={() => setSymbol(r.symbol)}
                        style={{ borderBottom: `1px solid ${colors.border}`, cursor: 'pointer' }}
                      >
                        <td style={{ padding: '8px 12px', fontWeight: 700, color: colors.text }}>{r.symbol}</td>
                        <td style={{ padding: '8px 12px', color: colors.textDim, maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.company_name || '—'}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', color: scoreColor, fontWeight: 700 }}>
                          {score !== null ? score.toFixed(1) : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div style={{ fontSize: 11, color: colors.textMuted, marginTop: 12, lineHeight: 1.6 }}>
            Showing {filteredUniverse.length} of {universe.length} · To refresh ranks:{' '}
            <code style={{ background: colors.panel2, padding: '1px 6px', borderRadius: 3, color: colors.text }}>python -m engine_perx.pe_signals --persist</code>
          </div>
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
        {/* ── Bottom Line (executive synthesis at the top) ── */}
        {report.bottom_line && report.bottom_line.summary && (() => {
          const bl = report.bottom_line!;
          const actionStyles: Record<string, { label: string; color: string; bg: string }> = {
            positive: { label: 'Strong setup', color: colors.strong, bg: '#052e16' },
            watch:    { label: 'Watch',        color: colors.accent, bg: '#0c2541' },
            cautious: { label: 'Caution',      color: colors.warn,   bg: '#3a2410' },
            negative: { label: 'Avoid',        color: colors.bad,    bg: '#3b0a0a' },
            no_data:  { label: 'Insufficient', color: colors.textMuted, bg: '#1c1c1c' },
          };
          const a = actionStyles[bl.action] || actionStyles.no_data;
          return (
            <div style={{ padding: '24px 40px', background: a.bg, borderBottom: `3px solid ${a.color}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <span style={{ display: 'inline-block', padding: '4px 10px', background: a.color, color: '#020617', fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.15em', borderRadius: 3 }}>BOTTOM LINE</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: a.color }}>{a.label}</span>
              </div>
              <div style={{ fontSize: 14, color: colors.text, lineHeight: 1.55, fontWeight: 500, marginBottom: 14 }}>
                {bl.summary}
              </div>
              <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: 6 }}>
                Across the 5 dimensions:
              </div>
              <div>
                {bl.highlights.map(h => {
                  const hlColor = (alignmentLabel[h.status] || alignmentLabel.no_data).color;
                  return (
                    <span key={h.signal} style={{ display: 'inline-block', padding: '4px 10px', margin: '3px 4px 3px 0', background: '#0b1220', border: `1px solid ${hlColor}`, borderRadius: 4, fontSize: 11, color: colors.text }}>
                      <span style={{ color: hlColor, fontWeight: 700 }}>{h.status_label}</span>
                      <span style={{ color: colors.textMuted }}> &middot; </span>
                      <span style={{ color: colors.textDim }}>{h.signal}</span>
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })()}
        {/* ── Manager Track Record strip ── */}
        {report.credibility && report.credibility.verdict_zone && (() => {
          const cred = report.credibility!;
          const streakColor = cred.consecutive_miss_quarters >= 4 ? colors.bad : cred.consecutive_miss_quarters >= 2 ? colors.warn : colors.text;
          return (
            <div style={{ padding: '20px 40px', background: '#0b1220', borderBottom: `1px solid ${colors.border}` }}>
              <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 14 }}>
                Manager Track Record
              </div>
              <div style={{ display: 'flex', gap: 36, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Accuracy</div>
                  <div style={{ fontSize: 32, fontWeight: 800, color: colors.text, lineHeight: 1, marginTop: 6 }}>
                    {cred.accuracy_pct !== null && cred.accuracy_pct !== undefined ? `${cred.accuracy_pct.toFixed(0)}%` : '—'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Verdict</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: verdictColor(cred.verdict_zone), marginTop: 14 }}>
                    {cred.verdict_zone}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Trend</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: trendColor(cred.trend), marginTop: 14 }}>
                    {cred.trend || '—'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Miss Streak</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: streakColor, marginTop: 14 }}>
                    {cred.consecutive_miss_quarters}Q
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Lag Score</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: colors.text, marginTop: 14 }}>
                    {cred.lag_score !== null && cred.lag_score !== undefined ? cred.lag_score.toFixed(0) : '—'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Promises</div>
                  <div style={{ fontSize: 13, color: colors.text, lineHeight: 1.5, marginTop: 12 }}>
                    {cred.achieved_count} achieved · {cred.missed_count} missed<br />
                    <span style={{ color: colors.textMuted }}>of {cred.total_promises} total</span>
                  </div>
                </div>
              </div>
              <div style={{ fontSize: 12, color: colors.textDim, marginTop: 12, fontStyle: 'italic', lineHeight: 1.5 }}>
                {cred.summary}
              </div>
            </div>
          );
        })()}

        {/* ── What Other Checks Say (Independent Check + Financial Quality + Price Action) ── */}
        {(() => {
          const ic = report.independent_check;
          const fq = report.financial_quality;
          const pa = report.price_action;
          const renderCard = (title: string, score: number | null | undefined, extra: ReactNode) => {
            const v = scoreVerdict(score);
            return (
              <div style={{ flex: 1, minWidth: 240, padding: '18px 20px', background: '#0b1220', border: `1px solid ${colors.border}`, borderRadius: 6 }}>
                <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: 10 }}>
                  {title}
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 8 }}>
                  <div style={{ fontSize: 36, fontWeight: 800, color: colors.text, lineHeight: 1 }}>
                    {score !== null && score !== undefined ? `${Math.round(score)}/100` : '—'}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: v.color }}>{v.label}</div>
                </div>
                {extra}
              </div>
            );
          };
          return (
            <div style={{ padding: '24px 40px', background: colors.panel, borderBottom: `1px solid ${colors.border}` }}>
              <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 14 }}>
                What Other Checks Say
              </div>
              <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
                {renderCard('Independent Check', ic?.master_score ?? null, (
                  <div>
                    {ic && ic.reasons && ic.reasons.length > 0 ? (
                      <ul style={{ margin: '8px 0 0 0', paddingLeft: 18 }}>
                        {ic.reasons.slice(0, 3).map((r, i) => (
                          <li key={i} style={{ margin: '3px 0', color: colors.textDim, fontSize: 11, lineHeight: 1.5 }}>{r}</li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ fontSize: 11, color: colors.textMuted, marginTop: 4 }}>No audit available</div>
                    )}
                  </div>
                ))}
                {renderCard('Financial Quality', fq?.score ?? null, (
                  <div>
                    {fq && fq.category ? (
                      <div style={{ fontSize: 11, color: colors.textDim, marginTop: 4 }}>
                        Category: <span style={{ color: colors.text, fontWeight: 600 }}>{fq.category}</span>
                      </div>
                    ) : (
                      <div style={{ fontSize: 11, color: colors.textMuted, marginTop: 4 }}>No verdict available</div>
                    )}
                  </div>
                ))}
                {renderCard('Price Action', pa?.total_score ?? null, (
                  <div>
                    {pa && pa.breakout_state ? (
                      <div style={{ fontSize: 11, color: colors.textDim, marginTop: 4 }}>
                        State: <span style={{ color: colors.text, fontWeight: 600 }}>{pa.breakout_state}</span>
                      </div>
                    ) : (
                      <div style={{ fontSize: 11, color: colors.textMuted, marginTop: 4 }}>No data available</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })()}

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
                {' · '}Manual refresh only — re-score via CLI
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
                <Fragment key={c.code}>
                <tr>
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
                {!c.missing && c.quote && (() => {
                  const q = c.quote;
                  const attribution = q.quarter
                    ? (q.source ? `${q.source} (${q.quarter})` : q.quarter)
                    : (q.source || 'transcript');
                  const barColor = c.signal_strength >= 4 ? colors.strong : c.signal_strength >= 3 ? colors.accent : colors.textMuted;
                  return (
                    <tr>
                      <td colSpan={5} style={{ padding: '0 12px 14px 12px', borderBottom: `1px solid ${colors.panel2}` }}>
                        <div style={{ borderLeft: `3px solid ${barColor}`, padding: '8px 12px', color: colors.textDim, fontSize: 11, fontStyle: 'italic', lineHeight: 1.55, background: '#0b1220', borderRadius: '0 4px 4px 0' }}>
                          &ldquo;{q.text}&rdquo;
                          <div style={{ color: colors.textMuted, fontStyle: 'normal', fontSize: 10, marginTop: 4 }}>— {attribution}</div>
                        </div>
                      </td>
                    </tr>
                  );
                })()}
                {!c.missing && c.status_grid && c.status_grid.length > 0 && (
                  <tr>
                    <td colSpan={5} style={{ padding: '0 12px 12px 12px', borderBottom: `1px solid ${colors.panel2}` }}>
                      <div style={{ background: colors.bg, border: `1px solid ${colors.border}`, borderRadius: 4, padding: '10px 12px' }}>
                        <div style={{ fontSize: 10, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: 8 }}>
                          Promise Status — last {c.status_grid.length} quarters
                        </div>
                        <table style={{ borderCollapse: 'collapse', fontSize: 11, color: '#cbd5e1' }}>
                          <thead>
                            <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
                              <th align="left" style={{ padding: '4px 8px', color: colors.textMuted, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>Quarter</th>
                              {['FULFILLED', 'ON_TRACK', 'PARTIALLY_FULFILLED', 'MISSED', 'REVISED_UP', 'REVISED_DOWN'].map(s => (
                                <th key={s} align="center" style={{ padding: '4px 6px', color: statusColor(s), fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>{s.replace(/_/g, ' ').replace('PARTIALLY', 'PART').slice(0, 7)}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {c.status_grid.map(g => (
                              <tr key={g.quarter} style={{ borderBottom: `1px solid ${colors.panel2}` }}>
                                <td style={{ padding: '4px 8px', fontFamily: 'monospace', color: colors.text }}>{g.quarter}</td>
                                {['FULFILLED', 'ON_TRACK', 'PARTIALLY_FULFILLED', 'MISSED', 'REVISED_UP', 'REVISED_DOWN'].map(s => {
                                  const n = g.counts[s] || 0;
                                  return (
                                    <td key={s} align="center" style={{ padding: '4px 6px', fontFamily: 'monospace', fontWeight: 600, color: n > 0 ? statusColor(s) : colors.textMuted }}>
                                      {n > 0 ? n : '·'}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}
              <tr>
                <td colSpan={3} style={{ padding: '14px 12px', color: colors.textDim, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Total</td>
                <td style={{ padding: '14px 12px', textAlign: 'right', color: colors.text, fontWeight: 800, fontSize: 15 }}>{report.totals.raw_score} / {report.totals.max_possible}</td>
                <td style={{ padding: '14px 12px', color: bucketC, fontWeight: 700 }}>{report.totals.scaled_percent}%</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* ── Where the Signals Agree (cross-check matrix) ── */}
        {report.cross_check && report.cross_check.length > 0 && (
          <div style={{ padding: '24px 40px', background: '#0b1220', borderTop: `1px solid ${colors.panel2}` }}>
            <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 6 }}>
              Where the Signals Agree
            </div>
            <div style={{ fontSize: 12, color: colors.textDim, marginBottom: 14, fontStyle: 'italic' }}>
              Whether the four engines back each other up.
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, color: '#cbd5e1' }}>
              <thead>
                <tr style={{ background: colors.bg, borderBottom: `1px solid ${colors.border}` }}>
                  <th align="left" style={{ padding: '8px 12px', color: colors.textMuted, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Dimension</th>
                  <th align="left" style={{ padding: '8px 12px', color: colors.textMuted, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Narrative</th>
                  <th align="left" style={{ padding: '8px 12px', color: colors.textMuted, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Independent Check</th>
                  <th align="left" style={{ padding: '8px 12px', color: colors.textMuted, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Financial Quality</th>
                  <th align="left" style={{ padding: '8px 12px', color: colors.textMuted, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Price Action</th>
                  <th align="left" style={{ padding: '8px 12px', color: colors.textMuted, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {report.cross_check.map(row => {
                  const a = alignmentLabel[row.alignment] || alignmentLabel.no_data;
                  return (
                    <tr key={row.dimension} style={{ borderBottom: `1px solid ${colors.panel2}` }}>
                      <td style={{ padding: '10px 12px', color: colors.text, fontWeight: 700 }}>{row.dimension}</td>
                      <td style={{ padding: '10px 12px', color: colors.textDim, fontSize: 11 }}>{row.pe_view}</td>
                      <td style={{ padding: '10px 12px', color: colors.textDim, fontSize: 11 }}>{row.indep_view}</td>
                      <td style={{ padding: '10px 12px', color: colors.textDim, fontSize: 11 }}>{row.fin_view}</td>
                      <td style={{ padding: '10px 12px', color: colors.textDim, fontSize: 11 }}>{row.price_view}</td>
                      <td style={{ padding: '10px 12px', color: a.color, fontWeight: 700, fontSize: 12 }}>{a.label}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Financial Quality breakdown ── */}
        {report.financial_quality && report.financial_quality.agents && (
          <div style={{ padding: '24px 40px', background: colors.panel, borderTop: `1px solid ${colors.panel2}` }}>
            <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 14 }}>
              Financial Quality — 7-Agent Breakdown
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, color: '#cbd5e1' }}>
              <tbody>
                {([
                  ['revenue',     'Revenue Quality'],
                  ['margin',      'Margin Quality'],
                  ['leverage',    'Leverage'],
                  ['wc',          'Working Capital'],
                  ['roce',        'Capital Efficiency (ROCE)'],
                  ['evolution',   'Business Evolution'],
                  ['translation', 'Financial Translation'],
                ] as [string, string][]).map(([key, label]) => {
                  const score = report.financial_quality!.agents[key as keyof typeof report.financial_quality.agents];
                  if (score === null || score === undefined) {
                    return (
                      <tr key={key} style={{ borderBottom: `1px solid ${colors.panel2}` }}>
                        <td style={{ padding: '8px 12px', color: colors.text }}>{label}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#475569', fontWeight: 700 }}>—</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#475569', letterSpacing: '0.05em' }}>{'░'.repeat(10)}</td>
                      </tr>
                    );
                  }
                  const s = score as number;
                  const rowColor = s >= 7 ? colors.strong : s >= 4 ? colors.warn : colors.bad;
                  return (
                    <tr key={key} style={{ borderBottom: `1px solid ${colors.panel2}` }}>
                      <td style={{ padding: '8px 12px', color: colors.text }}>{label}</td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: rowColor, fontWeight: 700 }}>{s}/10</td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: rowColor, letterSpacing: '0.05em' }}>{'█'.repeat(s)}{'░'.repeat(10 - s)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Price Action 7-step checklist ── */}
        {report.price_action && report.price_action.conditions && (() => {
          const conds: [string, string][] = [
            ['ema_50_200',    'EMA 50 above 200'],
            ['ema_200_slope', '200-day EMA slope positive'],
            ['six_m_high',    'Near 6-month high'],
            ['volume',        'Volume confirmation (1.3x)'],
            ['rs',            'Relative strength vs Nifty'],
            ['breakout_10d',  'Close above 10-day high'],
            ['price_quality', 'Strong close (70%+ of day\u2019s range)'],
          ];
          const nPass = conds.filter(([k]) => report.price_action!.conditions[k as keyof typeof report.price_action.conditions]).length;
          return (
            <div style={{ padding: '24px 40px', background: '#0b1220', borderTop: `1px solid ${colors.panel2}` }}>
              <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 6 }}>
                Price Action — 7-Step Checklist
              </div>
              <div style={{ fontSize: 12, color: colors.textDim, marginBottom: 14, fontStyle: 'italic' }}>
                {report.price_action.breakout_state} · {nPass} of 7 momentum signals on
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, color: '#cbd5e1' }}>
                <tbody>
                  {conds.map(([k, label]) => {
                    const passed = report.price_action!.conditions[k as keyof typeof report.price_action.conditions];
                    const color = passed ? colors.strong : colors.bad;
                    return (
                      <tr key={k} style={{ borderBottom: `1px solid ${colors.panel2}` }}>
                        <td style={{ padding: '8px 12px', fontFamily: 'monospace', color, fontWeight: 700, fontSize: 14, width: 32 }}>{passed ? '✓' : '✗'}</td>
                        <td style={{ padding: '8px 12px', color: colors.text }}>{label}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })()}

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
