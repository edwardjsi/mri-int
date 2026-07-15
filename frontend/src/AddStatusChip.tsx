import React, { useState, useEffect } from 'react';
import { api } from './api';

// Decision 103 V2 — AddStatusChip
// 4-state chip for the BreakoutRadar "ADD Status" column.
// Hover for quick tooltip, click for full modal.

type FinalState = 'OBSERVE' | 'APPROACHING_ADD' | 'READY_FOR_ADD' | 'ADD_SECOND_TRANCHE';

const stateMap: Record<FinalState, { emoji: string; label: string; color: string }> = {
  OBSERVE:            { emoji: '\u23F3', label: 'Observe',            color: '#6b7280' },
  APPROACHING_ADD:    { emoji: '\uD83D\uDC40', label: 'Approaching Add',    color: '#3b82f6' },
  READY_FOR_ADD:      { emoji: '\u26A1', label: 'Ready For Add',      color: '#f59e0b' },
  ADD_SECOND_TRANCHE: { emoji: '\u2705', label: 'Add 2nd Tranche',    color: '#22c55e' },
};

const gateLabels: Record<string, string> = {
  G1_DECISION_SCORE_BELOW_MIN:     'Decision Score \u2265 85',
  G2_MRI_TECHNICAL_BELOW_MIN:      'MRI Technical \u2265 80',
  G3_WEEKLY_CLOSE_BELOW_RESISTANCE: 'Weekly Close > Resistance',
  G4_VOLUME_NOT_CONFIRMED:         'Volume \u2265 1.3\u00D7 20d Avg',
  G5_BREAKOUT_AGE_TOO_OLD:         'Breakout Age \u2264 15d',
  CONFIDENCE_STARS_BELOW_MIN:      'Confidence Stars \u2265 4',
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
  try { return localStorage.getItem('mri_client_id'); } catch { return null; }
};

const AddStatusChip: React.FC<Props> = ({ symbol, clientId }) => {
  const resolvedClientId = clientId ?? getClientId();
  const [eligibility, setEligibility] = useState<Eligibility | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [hovered, setHovered] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);

  useEffect(() => {
    if (!resolvedClientId) {
      setLoading(false);
      setEligibility({
        symbol, client_id: '', has_existing_position: false,
        final_state: null, error: 'no_client_id',
        message: 'No client_id available \u2014 sign in to see gate state.',
      });
      return;
    }
    let cancelled = false;
    setLoading(true);
    api.getAddEligibility(symbol, resolvedClientId)
      .then((data: Eligibility) => { if (!cancelled) setEligibility(data); })
      .catch((err) => {
        if (!cancelled) setEligibility({
          symbol, client_id: resolvedClientId, has_existing_position: false,
          final_state: null, error: 'fetch_failed', message: err?.message || String(err),
        });
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [symbol, resolvedClientId]);

  if (loading) {
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center',
        backgroundColor: '#6b728020', color: '#6b7280',
        padding: '2px 6px', borderRadius: '4px', fontSize: '10px',
        fontWeight: 'bold', border: '1px solid #6b728040', marginLeft: '8px',
      }}>{'\u23F3'} {'\u2026'}</span>
    );
  }

  if (!eligibility || !eligibility.final_state) {
    const errMsg = eligibility?.message || 'CAS recommendation not yet generated.';
    return (
      <span title={errMsg} style={{
        display: 'inline-flex', alignItems: 'center',
        backgroundColor: '#6b728020', color: '#6b7280',
        padding: '2px 6px', borderRadius: '4px', fontSize: '10px',
        fontWeight: 'bold', border: '1px solid #6b728040', marginLeft: '8px',
        cursor: 'pointer',
      }} onClick={() => setShowModal(true)}>
        {'\u23F3'} OBSERVE
      </span>
    );
  }

  const meta = stateMap[eligibility.final_state] || stateMap.OBSERVE;
  const gr = eligibility.gate_result;

  return (
    <>
      {/* Chip + hover tooltip */}
      <span
        style={{ position: 'relative', display: 'inline-block' }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <span
          onClick={() => setShowModal(true)}
          style={{
            display: 'inline-flex', alignItems: 'center',
            backgroundColor: `${meta.color}20`, color: meta.color,
            padding: '2px 6px', borderRadius: '4px', fontSize: '10px',
            fontWeight: 'bold', border: `1px solid ${meta.color}40`,
            marginLeft: '8px', cursor: 'pointer',
            transition: 'background-color 0.2s',
          }}
        >
          {meta.emoji} {meta.label}
        </span>

        {hovered && !showModal && (
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0,
            zIndex: 1000, backgroundColor: '#1f2937', color: '#f3f4f6',
            padding: '8px 12px', borderRadius: '6px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            minWidth: '220px', fontSize: '12px', lineHeight: '1.5',
            border: '1px solid #374151', pointerEvents: 'none',
          }}>
            <div style={{ fontWeight: 'bold', color: meta.color, marginBottom: '4px' }}>
              {meta.emoji} {meta.label}
            </div>
            {eligibility.cas_score != null && (
              <div style={{ color: '#9ca3af' }}>
                CAS: <span style={{ color: '#f3f4f6' }}>{Number(eligibility.cas_score).toFixed(1)}</span>
              </div>
            )}
            {gr && (
              <div style={{ color: '#9ca3af' }}>
                Gates: <span style={{ color: meta.color }}>{gr.passed}/{gr.total} passed</span>
              </div>
            )}
            <div style={{ color: '#6b7280', fontSize: '11px', marginTop: '4px' }}>
              Click for details \u2192
            </div>
          </div>
        )}
      </span>

      {/* Full-screen modal */}
      {showModal && (
        <div
          onClick={() => setShowModal(false)}
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            zIndex: 9999, backgroundColor: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '20px',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: '#1e293b',
              color: '#f1f5f9',
              borderRadius: '16px',
              boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
              maxWidth: '600px',
              width: '100%',
              maxHeight: '90vh',
              overflow: 'auto',
              padding: '0',
              border: '1px solid #334155',
            }}
          >
            {/* Modal header */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '20px 24px', borderBottom: '1px solid #334155',
            }}>
              <div>
                <span style={{ fontSize: '13px', color: '#94a3b8' }}>{symbol}</span>
                <h2 style={{ margin: '4px 0 0', fontSize: '20px', fontWeight: 'bold', color: meta.color }}>
                  {meta.emoji} {meta.label}
                </h2>
              </div>
              <button
                onClick={() => setShowModal(false)}
                style={{
                  background: 'none', border: 'none', color: '#94a3b8', fontSize: '24px',
                  cursor: 'pointer', padding: '4px 8px', borderRadius: '6px',
                  lineHeight: 1,
                }}
              >
                {'\u2715'}
              </button>
            </div>

            {/* Modal body */}
            <div style={{ padding: '20px 24px 24px' }}>

              {/* Key metrics grid */}
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                gap: '12px', marginBottom: '20px',
              }}>
                {eligibility.cas_score != null && (
                  <div style={{ background: '#0f172a', padding: '12px 16px', borderRadius: '10px' }}>
                    <div style={{ color: '#64748b', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>CAS Score</div>
                    <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#f8fafc' }}>{Number(eligibility.cas_score).toFixed(1)}</div>
                  </div>
                )}
                {eligibility.cas_action && (
                  <div style={{ background: '#0f172a', padding: '12px 16px', borderRadius: '10px' }}>
                    <div style={{ color: '#64748b', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Action</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#f8fafc' }}>{eligibility.cas_action}</div>
                  </div>
                )}
                <div style={{ background: '#0f172a', padding: '12px 16px', borderRadius: '10px' }}>
                  <div style={{ color: '#64748b', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Position</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: eligibility.has_existing_position ? '#22c55e' : '#ef4444' }}>
                    {eligibility.has_existing_position ? '\u2705 YES' : '\u26D4 NO'}
                  </div>
                </div>
                {eligibility.breakout_state && (
                  <div style={{ background: '#0f172a', padding: '12px 16px', borderRadius: '10px' }}>
                    <div style={{ color: '#64748b', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Breakout</div>
                    <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{eligibility.breakout_state}</div>
                  </div>
                )}
              </div>

              {/* Gate section */}
              {gr && (
                <>
                  {/* Gate summary */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '12px',
                    marginBottom: '16px', padding: '12px 16px',
                    background: '#0f172a', borderRadius: '10px',
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 'bold', color: '#e2e8f0' }}>
                          Gate Progress
                        </span>
                        <span style={{ fontSize: '13px', fontWeight: 'bold', color: meta.color }}>
                          {gr.passed}/{gr.total} passed ({gr.score_pct}%)
                        </span>
                      </div>
                      <div style={{
                        height: '10px', backgroundColor: '#334155', borderRadius: '5px', overflow: 'hidden',
                      }}>
                        <div style={{
                          width: `${(gr.passed / gr.total) * 100}%`, height: '100%',
                          backgroundColor: gr.passed === gr.total ? '#22c55e' : '#f59e0b',
                          borderRadius: '5px', transition: 'width 0.3s',
                        }} />
                      </div>
                    </div>
                  </div>

                  {/* Gate rows */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {gateOrder.map((code) => {
                      const blocked = gr.blocked?.includes(code);
                      const passed = !blocked;
                      return (
                        <div key={code} style={{
                          display: 'flex', alignItems: 'center', gap: '12px',
                          padding: '12px 16px',
                          borderRadius: '10px',
                          backgroundColor: passed ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                          border: `1px solid ${passed ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
                        }}>
                          <div style={{
                            width: '36px', height: '36px', borderRadius: '50%',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '16px', fontWeight: 'bold', flexShrink: 0,
                            backgroundColor: passed ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)',
                            color: passed ? '#22c55e' : '#ef4444',
                          }}>
                            {passed ? '\u2713' : '\u2717'}
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{
                              fontSize: '14px', fontWeight: passed ? 'normal' : 'bold',
                              color: passed ? '#86efac' : '#fca5a5',
                            }}>
                              {gateLabels[code] || code}
                            </div>
                          </div>
                          <span style={{
                            fontSize: '13px', fontWeight: 'bold', padding: '4px 14px',
                            borderRadius: '20px', flexShrink: 0,
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

              {/* What needs to improve */}
              {gr && gr.blocked.length > 0 && (
                <div style={{
                  marginTop: '20px', padding: '14px 16px',
                  background: 'rgba(59,130,246,0.1)', borderRadius: '10px',
                  border: '1px solid rgba(59,130,246,0.3)',
                }}>
                  <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#93c5fd', marginBottom: '6px' }}>
                    {'\uD83D\uDCA1'} What needs to improve
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '13px', lineHeight: '1.6' }}>
                    {gr.blocked.map(code => (
                      <li key={code}>{gateLabels[code] || code} \u2014 currently <strong style={{ color: '#fca5a5' }}>FAILED</strong></li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AddStatusChip;
