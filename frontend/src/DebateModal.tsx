// @ts-nocheck
import { useState, useEffect } from 'react';
import { api } from './api';

/**
 * DebateModal — Bear vs Bull debate modal (FeatureRequest 2026-06-19).
 *
 * Props:
 *   symbol:           stock symbol
 *   contextKind:      'guidance' (Phase 2) | 'pe_expansion' (Phase 3)
 *   isOpen:           boolean
 *   onClose:          () => void
 *
 * Renders two side-by-side cards (Bear red, Bull green) plus optional
 * Adjudicator card. On open, fires POST /api/{contextKind}/{symbol}/debate.
 * Result is server-side cached, so re-opens are instant + free.
 */
export default function DebateModal({ symbol, contextKind = 'guidance', isOpen, onClose }: {
  symbol: string;
  contextKind?: 'guidance' | 'pe_expansion';
  isOpen: boolean;
  onClose: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [includeAdjudicator, setIncludeAdjudicator] = useState(false);

  useEffect(() => {
    if (!isOpen || !symbol) {
      setResult(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    const trigger = contextKind === 'pe_expansion' ? api.triggerPeExpansionDebate : api.triggerGuidanceDebate;
    trigger(symbol, { includeAdjudicator })
      .then((r: any) => setResult(r))
      .catch((e: any) => setError(e?.message || String(e)))
      .finally(() => setLoading(false));
  }, [isOpen, symbol, contextKind, includeAdjudicator]);

  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
        zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 20,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#020617', border: '1px solid #1e293b', borderRadius: 14,
          maxWidth: 1100, width: '100%', maxHeight: '92vh', overflow: 'auto',
          padding: 28, color: '#e2e8f0', fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ fontSize: '0.7rem', color: '#64748b', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 4 }}>
              🗣️ Bear vs Bull Debate
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc' }}>
              {symbol}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: 2 }}>
              Context: {contextKind === 'pe_expansion' ? 'Expansion Lens (PE rerating)' : 'GuidanceCheck (management integrity)'}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', color: '#94a3b8', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={includeAdjudicator}
                onChange={e => setIncludeAdjudicator(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              Include adjudicator (3rd call, +$0.001)
            </label>
            <button
              onClick={onClose}
              style={{
                padding: '6px 14px', background: '#1e293b', color: '#cbd5e1',
                border: '1px solid #334155', borderRadius: 8, fontSize: '0.85rem',
                cursor: 'pointer', fontWeight: 600,
              }}
            >
              ✕ Close
            </button>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div style={{ padding: 60, textAlign: 'center', color: '#64748b' }}>
            <div style={{ fontSize: '1rem', marginBottom: 8 }}>Generating debate…</div>
            <div style={{ fontSize: '0.78rem' }}>
              {includeAdjudicator ? 'Firing 3 LLM calls (bear + bull + adjudicator). ~10-15s.' : 'Firing 2 LLM calls (bear + bull). ~6-10s.'}
              <br />Cached after first run — re-opens are instant + free.
            </div>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div style={{ padding: 20, background: '#7f1d1d', borderRadius: 8, color: '#fff' }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>Debate failed</div>
            <div style={{ fontSize: '0.85rem' }}>{error}</div>
          </div>
        )}

        {/* Result */}
        {result && !loading && (
          <>
            {/* Meta strip */}
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: '0.72rem', color: '#64748b', marginBottom: 16, padding: '10px 14px', background: '#0f172a', borderRadius: 8, border: '1px solid #1e293b' }}>
              {result.cached && (
                <span style={{ color: '#4ade80', fontWeight: 700 }}>⚡ CACHED</span>
              )}
              <span>Model: <span style={{ color: '#cbd5e1', fontFamily: 'monospace' }}>{result.model_used || '—'}</span></span>
              <span>Generated: <span style={{ color: '#cbd5e1' }}>{result.generated_at ? new Date(result.generated_at).toLocaleString() : '—'}</span></span>
              {result.cache_hits > 0 && (
                <span>Cache hits: <span style={{ color: '#cbd5e1' }}>{result.cache_hits}</span></span>
              )}
              {result.context_hash && (
                <span style={{ fontFamily: 'monospace' }}>hash: {result.context_hash.slice(0, 12)}…</span>
              )}
            </div>

            {/* Bear + Bull side by side */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 14, marginBottom: 14 }}>
              <DebateCard
                label="BEAR"
                icon="🐻"
                bgColor="#1f0a0a"
                borderColor="#7f1d1d"
                textColor="#fca5a5"
                text={result.bear}
              />
              <DebateCard
                label="BULL"
                icon="🐂"
                bgColor="#0a1f0f"
                borderColor="#166534"
                textColor="#86efac"
                text={result.bull}
              />
            </div>

            {/* Adjudicator (if present) */}
            {result.adjudicator && (
              <AdjudicatorCard text={result.adjudicator} />
            )}

            {/* Stub fallback notice */}
            {(result.bear?.startsWith('[STUB') || result.bull?.startsWith('[STUB')) && (
              <div style={{ marginTop: 16, padding: 12, background: '#1c1c1c', border: '1px solid #475569', borderRadius: 8, fontSize: '0.8rem', color: '#fbbf24' }}>
                ⚠️ <strong>Stub output.</strong> No LLM API key configured — set
                <code style={{ background: '#020617', padding: '2px 6px', borderRadius: 4, margin: '0 4px' }}>DEEPSEEK_API_KEY</code>
                or
                <code style={{ background: '#020617', padding: '2px 6px', borderRadius: 4, margin: '0 4px' }}>OPENAI_API_KEY</code>
                to enable real bear/bull debates.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}


function DebateCard({ label, icon, bgColor, borderColor, textColor, text }: {
  label: string; icon: string; bgColor: string; borderColor: string; textColor: string; text: string;
}) {
  return (
    <div style={{
      background: bgColor, border: `1px solid ${borderColor}`,
      borderLeft: `4px solid ${borderColor}`, borderRadius: 10,
      padding: '16px 18px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: '1.3rem' }}>{icon}</span>
        <span style={{
          fontSize: '0.7rem', fontWeight: 800, letterSpacing: '0.15em',
          color: textColor, textTransform: 'uppercase',
        }}>
          {label} CASE
        </span>
      </div>
      <div style={{ fontSize: '0.88rem', color: '#e2e8f0', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
        {text}
      </div>
    </div>
  );
}


function AdjudicatorCard({ text }: { text: string }) {
  let parsed: any = null;
  try { parsed = JSON.parse(text); } catch { /* keep as raw */ }

  const winnerColor = parsed?.winner === 'bear' ? '#f87171'
                    : parsed?.winner === 'bull' ? '#4ade80'
                    : '#fbbf24';

  return (
    <div style={{
      background: '#1c1306', border: '1px solid #78350f',
      borderLeft: '4px solid #f59e0b', borderRadius: 10,
      padding: '16px 18px', marginBottom: 14,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: '1.3rem' }}>⚖️</span>
        <span style={{
          fontSize: '0.7rem', fontWeight: 800, letterSpacing: '0.15em',
          color: '#fbbf24', textTransform: 'uppercase',
        }}>
          ADJUDICATOR
        </span>
        {parsed && (
          <span style={{
            marginLeft: 'auto', padding: '4px 12px', background: winnerColor,
            color: '#020617', borderRadius: 16, fontSize: '0.72rem',
            fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>
            Winner: {parsed.winner} · {parsed.confidence ?? '?'}%
          </span>
        )}
      </div>
      {parsed ? (
        <div style={{ fontSize: '0.88rem', color: '#e2e8f0', lineHeight: 1.6 }}>
          <div style={{ marginBottom: 8 }}>{parsed.rationale}</div>
          {parsed.key_tipping_point && (
            <div style={{ fontSize: '0.78rem', color: '#94a3b8', fontStyle: 'italic' }}>
              Tipping point: <span style={{ color: '#fbbf24' }}>{parsed.key_tipping_point}</span>
            </div>
          )}
        </div>
      ) : (
        <div style={{ fontSize: '0.88rem', color: '#e2e8f0', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
          {text}
        </div>
      )}
    </div>
  );
}
