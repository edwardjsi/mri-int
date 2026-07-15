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
            padding: '14px',
            borderRadius: '8px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
            minWidth: '300px',
            maxWidth: '360px',
            fontSize: '13px',
            lineHeight: '1.5',
            border: '1px solid #374151',
          }}
        >
          {/* State header */}
          <div style={{
            fontWeight: 'bold',
            fontSize: '14px',
            marginBottom: '10px',
            color: meta.color,
            padding: '4px 10px',
            backgroundColor: `${meta.color}15`,
            borderRadius: '6px',
            display: 'inline-block',
          }}>
            {meta.emoji} {meta.label}
          </div>

          {/* Key metrics row — compact cards */}
          <div style={{
            display: 'flex',
            gap: '8px',
            flexWrap: 'wrap',
            marginBottom: '10px',
          }}>
            {eligibility.cas_score != null && (
              <div style={{ background: '#111827', padding: '4px 10px', borderRadius: '6px', minWidth: '60px' }}>
                <span style={{ color: '#6b7280', fontSize: '11px', display: 'block' }}>CAS</span>
                <span style={{ color: '#f3f4f6', fontWeight: 'bold', fontSize: '16px' }}>
                  {Number(eligibility.cas_score).toFixed(1)}
                </span>
              </div>
            )}
            {eligibility.cas_action && (
              <div style={{ background: '#111827', padding: '4px 10px', borderRadius: '6px' }}>
                <span style={{ color: '#6b7280', fontSize: '11px', display: 'block' }}>Action</span>
                <span style={{ color: '#f3f4f6', fontWeight: 'bold' }}>{eligibility.cas_action}</span>
              </div>
            )}
            {eligibility.has_existing_position !== undefined && (
              <div style={{ background: '#111827', padding: '4px 10px', borderRadius: '6px' }}>
                <span style={{ color: '#6b7280', fontSize: '11px', display: 'block' }}>Position</span>
                <span style={{
                  color: eligibility.has_existing_position ? '#22c55e' : '#ef4444',
                  fontWeight: 'bold',
                }}>
                  {eligibility.has_existing_position ? '✅ YES' : '⛔ NO'}
                </span>
              </div>
            )}
            {eligibility.breakout_state && (
              <div style={{ background: '#111827', padding: '4px 10px', borderRadius: '6px' }}>
                <span style={{ color: '#6b7280', fontSize: '11px', display: 'block' }}>Breakout</span>
                <span style={{ color: '#f3f4f6', fontWeight: 'bold', fontSize: '11px' }}>
                  {eligibility.breakout_state === 'BROKEN_OUT' ? '✅ Active' : eligibility.breakout_state}
                </span>
              </div>
            )}
          </div>

          {gr && (
            <>
              {/* Gate progress bar */}
              <div style={{
                display: 'flex',
                gap: '6px',
                marginBottom: '10px',
                padding: '6px 10px',
                backgroundColor: '#111827',
                borderRadius: '6px',
                alignItems: 'center',
              }}>
                <div style={{
                  flex: 1,
                  height: '8px',
                  backgroundColor: '#374151',
                  borderRadius: '4px',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${(gr.passed / gr.total) * 100}%`,
                    height: '100%',
                    backgroundColor: gr.passed === gr.total ? '#22c55e' : '#f59e0b',
                    borderRadius: '4px',
                    transition: 'width 0.3s',
                  }} />
                </div>
                <span style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                  {gr.passed}/{gr.total} gates
                  <span style={{ color: meta.color, marginLeft: '4px' }}>({gr.score_pct}%)</span>
                </span>
              </div>

              {/* Gate rows with colored backgrounds */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {gateOrder.map((code) => {
                  const blocked = gr.blocked?.includes(code);
                  const passed = !blocked;
                  return (
                    <div
                      key={code}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '5px 8px',
                        borderRadius: '5px',
                        backgroundColor: passed ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
                        border: `1px solid ${passed ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                      }}
                    >
                      <span style={{
                        color: passed ? '#4ade80' : '#fca5a5',
                        fontSize: '12px',
                        fontWeight: passed ? 'normal' : 'bold',
                      }}>
                        {passed ? '✓' : '✗'} {gateLabels[code] || code}
                      </span>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: 'bold',
                        padding: '1px 8px',
                        borderRadius: '4px',
                        color: passed ? '#22c55e' : '#ef4444',
                        backgroundColor: passed ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                      }}>
                        {passed ? 'PASS' : 'FAIL'}
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
