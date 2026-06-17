/**
 * ManagementIntegrityPanel — AAE × Management Integrity (Phase 5, 2026-06-17).
 *
 * Reusable React component that renders the management credibility
 * track-record block from `legacy_forensic.layers.management_integrity`.
 * Reads from the legacy forensic result of any AAE V3 scan, so it works
 * in any surface that calls /api/aae/scan/{symbol} (Digital Twin modal,
 * StockDetailsModal, future cards).
 *
 * Props:
 *   legacyForensic: the `legacy_forensic` dict from an AAE scan result,
 *                    OR the raw legacy orchestrator result with
 *                    `layers.management_integrity` directly.
 *   onNavigate:     optional (page: string) => void for the
 *                    "View Full Promise Timeline in GuidanceCheck" CTA.
 *
 * Renders:
 *   - Empty-state placeholder when has_data is false/missing
 *   - Score + verdict zone badge + trend + miss streak + lag score
 *   - LLM credibility assessment + verdict-flip warning
 *   - Master-score-contribution chip
 *   - Promise fulfillment chips (FULFILLED / REVISED_UP / ON_TRACK /
 *     PARTIALLY_FULFILLED / REVISED_DOWN / MISSED)
 *   - Graveyard rule alert (AUTO_BURY / SOFT_LAG_PENALTY / MANUAL_BURIAL)
 *   - "View Full Promise Timeline in GuidanceCheck →" CTA
 */

// Verdict zone color mapping — mirrors GuidanceCheck / ConvictionEngine conventions.
const VERDICT_ZONE_COLORS: Record<string, { bg: string; fg: string; border: string }> = {
  'ADD ZONE':      { bg: 'rgba(74, 222, 128, 0.15)',  fg: '#15803d', border: '#22c55e' },
  'HOLD ZONE':     { bg: 'rgba(251, 191, 36, 0.15)',  fg: '#b45309', border: '#f59e0b' },
  'REDUCE ZONE':   { bg: 'rgba(249, 115, 22, 0.15)',  fg: '#c2410c', border: '#f97316' },
  'THESIS BROKEN': { bg: 'rgba(244, 63, 94, 0.18)',   fg: '#be123c', border: '#e11d48' },
  'WATCHING':      { bg: 'rgba(100, 116, 139, 0.15)', fg: '#475569', border: '#64748b' },
};

const TREND_COLORS: Record<string, string> = {
  IMPROVING:        '#15803d',
  STABLE:           '#64748b',
  DETERIORATING:    '#b91c1c',
  INSUFFICIENT_DATA: '#94a3b8',
};

const PROMISE_STATUS_COLOR: Record<string, string> = {
  FULFILLED:             'rgba(74, 222, 128, 0.18)',
  REVISED_UP:            'rgba(74, 222, 128, 0.10)',
  ON_TRACK:              'rgba(59, 130, 246, 0.10)',
  PARTIALLY_FULFILLED:   'rgba(251, 191, 36, 0.18)',
  REVISED_DOWN:          'rgba(249, 115, 22, 0.18)',
  MISSED:                'rgba(244, 63, 94, 0.18)',
};

const PROMISE_STATUS_ORDER = [
  'FULFILLED', 'REVISED_UP', 'ON_TRACK', 'PARTIALLY_FULFILLED', 'REVISED_DOWN', 'MISSED',
];

interface Props {
  legacyForensic: any;
  onNavigate?: (page: string) => void;
}

export default function ManagementIntegrityPanel({ legacyForensic, onNavigate }: Props) {
  if (!legacyForensic) return null;

  const mi = legacyForensic.layers?.management_integrity;
  const graveyardRule = legacyForensic.graveyard_rule;
  const graveyardPenalty = legacyForensic.graveyard_penalty ?? 0;
  const credBreakdown = legacyForensic.master_score_breakdown?.credibility;

  // Graceful empty state when there's no credibility data yet.
  if (!mi || !mi.has_data) {
    return (
      <div style={{
        padding: '14px 16px',
        background: 'var(--soft)',
        borderRadius: '8px',
        border: '1px dashed var(--line)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '18px' }}>🛡️</span>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--muted)' }}>
              Management Integrity — no track record yet
            </div>
            <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>
              Credibility scoring activates once management has made enough verifiable promises.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const verdict = mi.verdict || 'WATCHING';
  const zoneColors = VERDICT_ZONE_COLORS[verdict] || VERDICT_ZONE_COLORS.WATCHING;
  const score = mi.credibility_score ?? 0;
  const trendColor = TREND_COLORS[mi.trend || 'INSUFFICIENT_DATA'] || TREND_COLORS.INSUFFICIENT_DATA;
  const counts = mi.promise_counts || {};
  const actionable = mi.actionable_promises ?? 0;
  const total = mi.total_promises ?? 0;
  const cons = mi.consecutive_miss_quarters ?? 0;

  const countChips = PROMISE_STATUS_ORDER
    .filter(k => (counts[k] || 0) > 0)
    .map(k => (
      <span key={k} style={{
        display: 'inline-flex', alignItems: 'baseline', gap: '4px',
        padding: '3px 10px', borderRadius: '999px',
        background: PROMISE_STATUS_COLOR[k], border: '1px solid var(--line)',
        fontSize: '11px', fontWeight: 600, color: 'var(--text)',
      }}>
        <span style={{ fontWeight: 800 }}>{counts[k]}</span>
        <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.3px', color: 'var(--muted)' }}>
          {k.replace(/_/g, ' ')}
        </span>
      </span>
    ));

  const graveyardAlert = (() => {
    if (graveyardRule === 'AUTO_BURY') {
      return (
        <div style={{
          padding: '10px 14px',
          background: 'rgba(244, 63, 94, 0.10)',
          borderLeft: '3px solid #e11d48',
          borderRadius: '6px',
          fontSize: '12px', fontWeight: 700, color: '#9f1239',
        }}>
          ⚠ Auto-buried by credibility collapse rule (−{graveyardPenalty} pts applied)
        </div>
      );
    }
    if (graveyardRule === 'SOFT_LAG_PENALTY') {
      return (
        <div style={{
          padding: '10px 14px',
          background: 'rgba(251, 191, 36, 0.10)',
          borderLeft: '3px solid #f59e0b',
          borderRadius: '6px',
          fontSize: '12px', fontWeight: 700, color: '#b45309',
        }}>
          ⚠ Credibility warning — soft lag penalty (−{graveyardPenalty} pts applied)
        </div>
      );
    }
    if (graveyardRule === 'MANUAL_BURIAL') {
      return (
        <div style={{
          padding: '10px 14px',
          background: 'rgba(244, 63, 94, 0.10)',
          borderLeft: '3px solid #e11d48',
          borderRadius: '6px',
          fontSize: '12px', fontWeight: 700, color: '#9f1239',
        }}>
          ⚠ Forensically rejected (manually buried, −{graveyardPenalty} pts applied)
        </div>
      );
    }
    return null;
  })();

  return (
    <div style={{
      padding: '16px',
      background: 'var(--soft)',
      borderRadius: '8px',
      border: '1px solid var(--line)',
    }}>
      {/* Header row: score + verdict badge */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '22px' }}>🛡️</span>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text)' }}>
              Management Integrity
            </div>
            <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>
              Cross-transcript pledge tracking · {actionable} of {total} promises actionable
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ fontSize: '28px', fontWeight: 800, color: zoneColors.fg, lineHeight: 1 }}>
            {score.toFixed(1)}
          </div>
          <div style={{
            padding: '6px 14px',
            background: zoneColors.bg,
            border: `1px solid ${zoneColors.border}`,
            borderRadius: '999px',
            fontSize: '11px', fontWeight: 800, color: zoneColors.fg,
            textTransform: 'uppercase', letterSpacing: '0.4px',
          }}>
            {verdict}
          </div>
        </div>
      </div>

      {/* Secondary metrics row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
        {mi.trend && (
          <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: '6px', padding: '4px 10px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: '6px', fontSize: '11px' }}>
            <span style={{ color: 'var(--muted)' }}>Trend:</span>
            <span style={{ fontWeight: 700, color: trendColor }}>{mi.trend}</span>
          </span>
        )}
        {cons > 0 && (
          <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: '6px', padding: '4px 10px', background: 'rgba(244, 63, 94, 0.08)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '6px', fontSize: '11px' }}>
            <span style={{ color: 'var(--muted)' }}>Miss streak:</span>
            <span style={{ fontWeight: 700, color: '#9f1239' }}>{cons}Q consecutive</span>
          </span>
        )}
        {mi.lag_score != null && mi.lag_score > 0 && (
          <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: '6px', padding: '4px 10px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: '6px', fontSize: '11px' }}>
            <span style={{ color: 'var(--muted)' }}>Lag score:</span>
            <span style={{ fontWeight: 700, color: 'var(--text)' }}>{Number(mi.lag_score).toFixed(0)}/100</span>
          </span>
        )}
        {mi.narrative_assessment && mi.narrative_assessment !== 'INSUFFICIENT_DATA' && (
          <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: '6px', padding: '4px 10px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: '6px', fontSize: '11px' }}>
            <span style={{ color: 'var(--muted)' }}>LLM assessment:</span>
            <span style={{
              fontWeight: 800,
              color: mi.narrative_assessment === 'TRUSTED' ? '#15803d'
                   : mi.narrative_assessment === 'DISTRUSTED' ? '#9f1239'
                   : 'var(--text)',
            }}>{mi.narrative_assessment}</span>
          </span>
        )}
        {mi.verdict_flipped_recently && (
          <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: '6px', padding: '4px 10px', background: 'rgba(251, 191, 36, 0.15)', border: '1px solid #f59e0b', borderRadius: '6px', fontSize: '11px', fontWeight: 700, color: '#b45309' }}>
            ⚠ Verdict flipped: {mi.previous_verdict} → {mi.verdict}
          </span>
        )}
        {credBreakdown != null && (
          <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: '6px', padding: '4px 10px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: '6px', fontSize: '11px' }}>
            <span style={{ color: 'var(--muted)' }}>Master score contribution:</span>
            <span style={{ fontWeight: 700, color: 'var(--blue)' }}>+{Number(credBreakdown).toFixed(1)}</span>
          </span>
        )}
      </div>

      {/* Promise counts chips */}
      {countChips.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontSize: '10px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px', letterSpacing: '0.5px' }}>
            Promise Fulfillment
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {countChips}
          </div>
        </div>
      )}

      {/* Graveyard rule alert */}
      {graveyardAlert && <div style={{ marginTop: '12px' }}>{graveyardAlert}</div>}

      {/* CTA: navigate to GuidanceCheck for full timeline */}
      {onNavigate && (
        <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--line)' }}>
          <button
            type="button"
            onClick={() => onNavigate('guidance')}
            style={{
              background: 'transparent',
              border: '1px solid var(--line)',
              color: 'var(--blue)',
              fontSize: '12px', fontWeight: 700,
              padding: '8px 14px', borderRadius: '6px',
              cursor: 'pointer',
              display: 'inline-flex', alignItems: 'center', gap: '6px',
            }}
          >
            📜 View Full Promise Timeline in GuidanceCheck →
          </button>
        </div>
      )}
    </div>
  );
}
