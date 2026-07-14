interface Props {
  symbol: string;
  cas: number;
  confidenceStars: number;
  actionChip: 'BUY' | 'ADD' | 'WATCH' | 'NO_ACTION';
  whyChecklist: string[];
  breakoutAge: number;
  breakoutAgeEmoji: string;
}

/**
 * CapitalAllocationCard — Decision 104 (N+3 — Browser Visibility)
 * 
 * Renders the Capital Allocation Score (CAS) as a banner card:
 * - Symbol + CAS score (rounded to 1 decimal)
 * - Confidence ★ rating (model certainty, 0-5)
 * - Action chip (BUY / ADD / WATCH / NO_ACTION)
 * - Why-checklist (multi-line ✓ bullets)
 * 
 * This is the frontend component that makes Decision 100's CAS output
 * visible in the browser. Without it, the user can only see terminal output.
 */
export default function CapitalAllocationCard({
  symbol,
  cas,
  confidenceStars,
  actionChip,
  whyChecklist,
  breakoutAge,
  breakoutAgeEmoji
}: Props) {
  const starEmoji = '★'.repeat(confidenceStars) + '☆'.repeat(5 - confidenceStars);

  const borderColor = cas >= 85 ? '#22c55e' : cas >= 70 ? '#3b82f6' : cas >= 50 ? '#f59e0b' : '#64748b';

  return (
    <div className="capital-allocation-card" style={{
      padding: '16px',
      border: `1px solid ${borderColor}`,
      borderRadius: '8px',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
      marginBottom: '12px'
    }}>
      <div className="card-header" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '8px'
      }}>
        <div className="symbol-section" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#e2e8f0' }}>{symbol}</span>
          <span style={{ fontSize: '14px' }}>{breakoutAgeEmoji}</span>
          <span style={{ fontSize: '13px', color: '#64748b' }}>
            {breakoutAge === 0 ? 'Today' : breakoutAge <= 1 ? 'Yesterday' : `Day ${breakoutAge}`}
          </span>
        </div>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          backgroundColor: actionChip === 'ADD' ? '#22c55e20' : actionChip === 'BUY' ? '#3b82f620' : actionChip === 'WATCH' ? '#f59e0b20' : '#6b728020',
          color: actionChip === 'ADD' ? '#22c55e' : actionChip === 'BUY' ? '#3b82f6' : actionChip === 'WATCH' ? '#f59e0b' : '#6b7280',
          padding: '2px 6px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 'bold',
          border: `1px solid ${actionChip === 'ADD' ? '#22c55e40' : actionChip === 'BUY' ? '#3b82f640' : actionChip === 'WATCH' ? '#f59e0b40' : '#6b728040'}`,
        }}>{actionChip}</span>
      </div>

      <div className="cas-display" style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: '8px',
        marginBottom: '10px'
      }}>
        <span className="cas-score" style={{
          fontSize: '24px',
          fontWeight: 'bold',
          color: '#e2e8f0'
        }}>
          {cas.toFixed(1)}
        </span>
        <span className="confidence-stars" style={{
          fontSize: '14px',
          color: '#facc15'
        }}>
          {starEmoji}
        </span>
      </div>

      <div className="why-checklist" style={{
        fontSize: '12px',
        lineHeight: '1.6',
        color: '#94a3b8'
      }}>
        {whyChecklist.map((line, i) => (
          <div key={i} style={{ color: '#22c55e' }}>✓ {line}</div>
        ))}
      </div>
    </div>
  );
}