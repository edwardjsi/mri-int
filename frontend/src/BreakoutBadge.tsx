import React from 'react';

type BreakoutState = 'BROKEN_OUT' | 'READY_TO_BREAKOUT' | 'CONSOLIDATING' | string;

type AgeInfo = {
  label: string;
  emoji: string;
  zone: string;
};

type Props = {
  state: BreakoutState;
  ageInfo?: AgeInfo;
};

const stateMap: Record<string, { emoji: string; label: string; color: string }> = {
  BROKEN_OUT: { emoji: '🚀', label: 'Broken Out', color: '#22c55e' },
  READY_TO_BREAKOUT: { emoji: '⚡', label: 'Ready', color: '#f59e0b' },
  CONSOLIDATING: { emoji: '⏳', label: 'Consolidating', color: '#6b7280' },
};

const zoneColorMap: Record<string, string> = {
  fresh: '#22c55e',
  early: '#10b981',
  late: '#f59e0b',
  mature: '#64748b',
  coiling: '#3b82f6',
  none: '#6b7280',
  unknown: '#64748b',
};

const BreakoutBadge: React.FC<Props> = ({ state, ageInfo }) => {
  const fallback = stateMap[state] || { emoji: '❓', label: state, color: '#64748b' };
  
  const displayLabel = ageInfo ? ageInfo.label : fallback.label;
  const displayEmoji = ageInfo ? ageInfo.emoji : fallback.emoji;
  const displayColor = ageInfo ? zoneColorMap[ageInfo.zone] || fallback.color : fallback.color;

  return (
    <span
      title={displayLabel}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        backgroundColor: `${displayColor}20`,
        color: displayColor,
        padding: '2px 6px',
        borderRadius: '4px',
        fontSize: '10px',
        fontWeight: 'bold',
        border: `1px solid ${displayColor}40`,
        marginLeft: '8px',
        transition: 'background-color 0.2s, color 0.2s',
      }}
    >
      {displayEmoji} {displayLabel}
    </span>
  );
};

export default BreakoutBadge;
