import React from 'react';

type BreakoutState = 'BROKEN_OUT' | 'READY_TO_BREAKOUT' | 'CONSOLIDATING' | string;

type Props = {
  state: BreakoutState;
};

const stateMap: Record<string, { emoji: string; label: string; color: string }> = {
  BROKEN_OUT: { emoji: '🚀', label: 'Broken Out', color: '#22c55e' },
  READY_TO_BREAKOUT: { emoji: '⚡', label: 'Ready', color: '#f59e0b' },
  CONSOLIDATING: { emoji: '⏳', label: 'Consolidating', color: '#6b7280' },
};

const BreakoutBadge: React.FC<Props> = ({ state }) => {
  const info = stateMap[state] || { emoji: '❓', label: state, color: '#64748b' };
  return (
    <span
      title={info.label}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        backgroundColor: `${info.color}20`,
        color: info.color,
        padding: '2px 6px',
        borderRadius: '4px',
        fontSize: '10px',
        fontWeight: 'bold',
        border: `1px solid ${info.color}40`,
        marginLeft: '8px',
        transition: 'background-color 0.2s, color 0.2s',
      }}
    >
      {info.emoji} {info.label}
    </span>
  );
};

export default BreakoutBadge;
