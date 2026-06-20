import { useEffect, useState } from 'react';
import { apiFetch } from './api';

interface DebateResult {
  bear: string;
  bull: string;
  adjudicator: string | null;
  model_used: string;
  generated_at: string;
  cache_hits: number;
  cached: boolean;
}

interface Props {
  symbol: string;
  contextKind: 'guidance' | 'pe_expansion';
}

const colors = {
  bear: '#ef4444',      // red-500
  bull: '#22c55e',      // green-500
  text: '#e2e8f0',
  textMuted: '#94a3b8',
  textDim: '#64748b',
  bg: '#020617',
  cardBg: '#0b1220',
  border: '#1e293b',
};

/**
 * Embedded debate section — auto-loads cached debate on mount.
 *
 * Props:
 *   symbol      — stock symbol (e.g. "POLYCAB")
 *   contextKind — "guidance" or "pe_expansion" (determines API endpoint)
 *
 * Behavior:
 * 1. On mount: fires GET /api/{kind}/{symbol}/debate (read-only, instant on hit)
 * 2. If cached: renders bear/bull cards immediately
 * 3. If miss: shows "generate" placeholder with a button to trigger POST
 *
 * Cost: $0 on cache hit, ~$0.002 on user-triggered POST (no auto-fire).
 */
export default function EmbeddedDebateSection({ symbol, contextKind }: Props) {
  const [data, setData] = useState<DebateResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const endpoint = contextKind === 'guidance'
    ? `/api/guidance/${symbol}/debate`
    : `/api/pe-expansion/${symbol}/debate`;

  // Fetch cached debate on mount (GET — no LLM cost)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiFetch(endpoint, { method: 'GET' })
      .then((res: any) => {
        if (cancelled) return;
        if (res?.cached) {
          setData(res);
        } else {
          setData(null); // cache miss — leave empty,下游 renders placeholder
        }
      })
      .catch((err: any) => {
        if (!cancelled) setError(err?.message || 'Failed to load debate');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [symbol, contextKind, endpoint]);

  // User-triggered generation (POST — costs ~$0.002)
  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await apiFetch(endpoint, { method: 'POST' });
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to generate debate');
    } finally {
      setGenerating(false);
    }
  };

  // Skeleton state
  if (loading) {
    return (
      <div style={{ padding: '24px 40px', background: colors.cardBg, borderBottom: `1px solid ${colors.border}` }}>
        <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 14 }}>
          Bear vs Bull Synthesis
        </div>
        <div style={{ display: 'flex', gap: 20 }}>
          {[0, 1].map((i) => (
            <div key={i} style={{ flex: 1, minHeight: 120, background: '#0f172a', borderRadius: 6, animation: 'pulse 2s infinite' }} />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{ padding: '24px 40px', background: colors.cardBg, borderBottom: `1px solid ${colors.border}` }}>
        <div style={{ fontSize: 12, color: colors.bear }}>⚠️ {error}</div>
      </div>
    );
  }

  // Cache miss — user-trigger placeholder
  if (!data) {
    return (
      <div style={{ padding: '24px 40px', background: colors.cardBg, borderBottom: `1px solid ${colors.border}` }}>
        <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 14 }}>
          Bear vs Bull Synthesis
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, color: colors.textDim }}>
            No cached debate available for {symbol}.
          </span>
          <button
            onClick={handleGenerate}
            disabled={generating}
            style={{
              padding: '8px 16px',
              background: generating ? '#1e293b' : '#0ea5e9',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              fontSize: 12,
              fontWeight: 600,
              cursor: generating ? 'not-allowed' : 'pointer',
              opacity: generating ? 0.6 : 1,
            }}
          >
            {generating ? 'Generating… (~8s)' : 'Generate debate →'}
          </button>
        </div>
      </div>
    );
  }

  // Render bear + bull cards
  return (
    <div style={{ padding: '24px 40px', background: colors.cardBg, borderBottom: `1px solid ${colors.border}` }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <span style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.2em', textTransform: 'uppercase' }}>
          Bear vs Bull Synthesis
        </span>
        <span style={{ fontSize: 10, color: colors.textDim }}>
          {data.cached ? `cached (${data.cache_hits} hits)` : 'fresh'} · {data.model_used}
        </span>
      </div>

      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        {/* Bear Card */}
        <div style={{ flex: 1, minWidth: 280, borderLeft: `3px solid ${colors.bear}`, padding: '14px 18px', background: '#1a0a0a', borderRadius: 4 }}>
          <div style={{ fontSize: 10, color: colors.bear, textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 800, marginBottom: 8 }}>
            🐻 Bear Case
          </div>
          <div style={{ fontSize: 13, color: colors.text, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {data.bear}
          </div>
        </div>

        {/* Bull Card */}
        <div style={{ flex: 1, minWidth: 280, borderLeft: `3px solid ${colors.bull}`, padding: '14px 18px', background: '#0a1a0a', borderRadius: 4 }}>
          <div style={{ fontSize: 10, color: colors.bull, textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 800, marginBottom: 8 }}>
            🐂 Bull Case
          </div>
          <div style={{ fontSize: 13, color: colors.text, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {data.bull}
          </div>
        </div>
      </div>
    </div>
  );
}
