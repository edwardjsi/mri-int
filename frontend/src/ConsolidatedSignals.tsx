import { useState } from 'react';
import ShadowMomentumPage from './ShadowMomentumPage';
import One12CoDashboard from './One12CoDashboard';
import DarvasScreener from './DarvasScreener';
import BreakoutRadarPage from './BreakoutRadarPage';

export default function ConsolidatedSignals({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [activeTab, setActiveTab] = useState<'shadow' | '112co' | 'darvas' | 'radar'>('shadow');

  const tabStyle = (isActive: boolean) => ({
    padding: '12px 24px',
    cursor: 'pointer',
    background: isActive ? '#3b82f6' : '#1e293b',
    color: isActive ? 'white' : '#94a3b8',
    border: 'none',
    borderBottom: isActive ? '2px solid #60a5fa' : '2px solid transparent',
    fontWeight: isActive ? 600 : 400,
    fontSize: '15px',
    transition: 'all 0.2s ease',
    flex: 1
  });

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '24px 24px 0 24px' }}>
        <h1 className="page-title" style={{ marginBottom: '16px' }}>Signals Dashboard</h1>
        <div style={{ display: 'flex', background: '#1e293b', borderRadius: '8px 8px 0 0', overflow: 'hidden' }}>
          <button style={tabStyle(activeTab === 'shadow')} onClick={() => setActiveTab('shadow')}>
            🔄 Swing Momentum
          </button>
          <button style={tabStyle(activeTab === '112co')} onClick={() => setActiveTab('112co')}>
            🎯 112 CO
          </button>
          <button style={tabStyle(activeTab === 'darvas')} onClick={() => setActiveTab('darvas')}>
            📊 Darvas Screener
          </button>
          <button style={tabStyle(activeTab === 'radar')} onClick={() => setActiveTab('radar')}>
            📡 Breakout Radar
          </button>
        </div>
      </div>
      
      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: '24px' }}>
        {activeTab === 'shadow' && <ShadowMomentumPage onSelectStock={onSelectStock} />}
        {activeTab === '112co' && <One12CoDashboard onViewResearch={(symbol: string) => onSelectStock({ symbol })} />}
        {activeTab === 'darvas' && <DarvasScreener />}
        {activeTab === 'radar' && <BreakoutRadarPage onViewResearch={(symbol: string) => onSelectStock({ symbol })} />}
      </div>
    </div>
  );
}
