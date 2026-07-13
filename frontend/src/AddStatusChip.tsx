import React, { useState, useEffect } from 'react';
import { api } from './api';

// Decision 103 V2 — AddStatusChip
// 4-state chip for the BreakoutRadar "ADD Status" column.
// Sources: GET /api/cas/add-eligibility?symbol=X&client_id=Y
//          (calls engine evaluate_add_gates + compute_layered_state server-side)

type FinalState = 'OBSERVE' | 'APPROACHING_ADD' | 'READY_FOR_ADD' | 'ADD_SECOND_TRANCHE';

const stateMap: Record<FinalState, { emoji: string; label: string; color: string }> = {
  OBSERVE:            { emoji: '⏳', label: 'Observe',            color: '#6b7280' },  // gray
  APPROACHING_ADD:    { emoji: '👀', label: 'Approaching Add',    color: '#3b82f6' },  // blue
  READY_FOR_ADD:      { emoji: '⚡', label: 'Ready For Add',      color: '#f59e0b' },  // amber
  ADD_SECOND_TRANCHE: { emoji: '✅', label: 'Add 2nd Tranche',    color: '#22c55e' },  // green
};

// Machine-readable gate codes → human labels (matches GATE_BLOCK_CODES in
// engine_core/cas_recommendations.py — keep in sync if new gates added).
const gateLabels: Record<string, string> = {
  G1_DECISION_SCORE_BELOW_MIN:     'G1 — Decision Score ≥ 85',
  G2_MRI_TECHNICAL_BELOW_MIN:      'G2 — MRI Technical ≥ 80',
  G3_WEEKLY_CLOSE_BELOW_RESISTANCE: 'G3 — Weekly Close > Resistance',
  G4_VOLUME_NOT_CONFIRMED:         'G4 — Volume ≥ 1.3× 20d Avg',
  G5_BREAKOUT_AGE_TOO_OLD:         'G5 — Breakout Age ≤ 15d',
  CONFIDENCE_STARS_BELOW_MIN:      'Confidence Stars ≥ 4',
};

const gateOrder = [
  'G1_DECISION_SCORE_BELOW_MIN',
  'G2_MRI_TECHNICAL_BELOW_MIN',
  'G3_WEEKLY_CLOSE_BELOW_RESISTANCE',
  'G4_VOLUME_NOT_CONFIRMED',
  'G5_BREAKOUT_AGE_TOO_OLD',
  'CONFIDENCE_STARS_BELOW_MIN',
];

type Props = {
  symbol: string;
  clientId?: string;
};

type Eligibility = {
  symbol: string;
  client_id: string;
  has_existing_position: boolean;
  gate_inputs?: Record<string, any>;
  gate_result?: { passed: number; total: number; blocked: string[]; score_pct: number };
  final_state: FinalState | null;
  config_snapshot?: Record<string, any>;
  breakout_state?: string;
  cas_action?: string;
  cas_score?: number;
  resistance_source?: string | null;
  error?: string;
  message?: string;
};

const getClientId = (): string | null => {
  try {
    return localStorage.getItem('mri_client_id');
  } catch {
    return null;
  }
};

const AddStatusChip: React.FC<Props> = ({ symbol, clientId }) => {
  const resolvedClientId = clientId ?? getClientId();
  const [eligibility, setEligibility] = useState<Eligibility | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [hovered, setHovered] = useState<boolean>(false);

  useEffect(() => {
    if (!resolvedClientId) {
      setLoading(false);
      setEligibility({
        symbol,
        client_id: '',
        has_existing_position: false,
        final_state: null,
        error: 'no_client_id',
        message: 'No client_id available — sign in to see gate state.',
      });
      return;
    }
    let cancelled = false;
    setLoading(true);
    api
      .getAddEligibility(symbol, resolvedClientId)
      .then((data: Eligibility) => {
        if (!cancelled) setEligibility(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setEligibility({
            symbol,
            client_id: resolvedClientId,
            has_existing_position: false,
            final_state: null,
            error: 'fetch_failed',
            message: err?.message || String(err),
          });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, resolvedClientId]);

  // Loading state — neutral gray spinner
  if (loading) {
    return (
      <span
        title="Loading ADD eligibility…"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          backgroundColor: '#6b728020',
          color: '#6b7280',
          padding: '2px 6px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 'bold',
          border: '1px solid #6b728040',
          marginLeft: '8px',
        }}
      >
        ⏳ …
      </span>
    );
  }

  // Error / no-data state — render as OBSERVE with explanatory tooltip
  if (!eligibility || !eligibility.final_state) {
    const errMsg = eligibility?.message || 'CAS recommendation not yet generated — run indicator engine first.';
    return (
      <span
        title={errMsg}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          backgroundColor: '#6b728020',
          color: '#6b7280',
          padding: '2px 6px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 'bold',
          border: '1px solid #6b728040',
          marginLeft: '8px',
        }}
      >
        ⏳ OBSERVE
      </span>
    );
  }

  const meta = stateMap[eligibility.final_state] || stateMap.OBSERVE;
  const gr = eligibility.gate_result;
  const title = gr
    ? `${meta.label} — ${gr.passed}/${gr.total} gates passed (${gr.score_pct}%)`
    : meta.label;

  return (
    <span
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <span
        title={title}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          backgroundColor: `${meta.color}20`,
          color: meta.color,
          padding: '2px 6px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 'bold',
          border: `1px solid ${meta.color}40`,
          marginLeft: '8px',
          cursor: 'help',
          transition: 'background-color 0.2s, color 0.2s',
        }}
      >
        {meta.emoji} {meta.label}
      </span>

      {hovered && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            zIndex: 1000,
            backgroundColor: '#1f2937',
            color: '#f3f4f6',
            padding: '12px',
            borderRadius: '6px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            minWidth: '280px',
            fontSize: '11px',
            lineHeight: '1.4',
          }}
        >
          <div style={{ fontWeight: 'bold', fontSize: '12px', marginBottom: '6px', color: meta.color }}>
            {meta.emoji} {meta.label}
          </div>
          {eligibility.cas_score != null && (
            <div style={{ color: '#9ca3af' }}>
              CAS: <span style={{ color: '#f3f4f6' }}>{Number(eligibility.cas_score).toFixed(1)}</span>
              {eligibility.cas_action && <> · Action: <span style={{ color: '#f3f4f6' }}>{eligibility.cas_action}</span></>}
            </div>
          )}
          {eligibility.breakout_state && (
            <div style={{ color: '#9ca3af' }}>
              Breakout: <span style={{ color: '#f3f4f6' }}>{eligibility.breakout_state}</span>
            </div>
          )}
          {eligibility.resistance_source && (
            <div style={{ color: '#9ca3af' }}>
              Resistance: <span style={{ color: '#f3f4f6' }}>{eligibility.resistance_source}</span>
            </div>
          )}
          {eligibility.has_existing_position !== undefined && (
            <div style={{ color: '#9ca3af' }}>
              Existing Position: <span style={{ color: eligibility.has_existing_position ? '#22c55e' : '#f3f4f6' }}>
                {eligibility.has_existing_position ? 'YES' : 'NO'}
              </span>
            </div>
          )}

          {gr && (
            <>
              <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #374151' }}>
                <div style={{ color: '#9ca3af', marginBottom: '4px' }}>
                  Gates: <span style={{ color: meta.color, fontWeight: 'bold' }}>
                    {gr.passed}/{gr.total} passed ({gr.score_pct}%)
                  </span>
                </div>
                {gateOrder.map((code) => {
                  const blocked = gr.blocked?.includes(code);
                  const passed = !blocked;
                  return (
                    <div key={code} style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                      <span style={{ color: '#9ca3af' }}>{gateLabels[code] || code}</span>
                      <span style={{ color: passed ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                        {passed ? '✓' : '✗'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </span>
  );
};

export default AddStatusChip;
