import React, { useState, useEffect } from 'react';

// Mock data to simulate API responses for V2 dashboard
const MOCK_PORTFOLIO_HEALTH = {
  health_score: 85.0,
  total_positions: 10,
  state_distribution: { ADD: 2, HOLD: 5, ALERT: 1, STRUCTURE: 1, QUIT: 1 }
};

const MOCK_HOLDINGS = [
  { symbol: 'AAPL', decision: 'HOLD', confidence: 0.9, stability: 0.8, why: 'Trend is healthy', why_not_add: 'Portfolio weight already full', expiry: '2026-08-02', portfolio_pct: 12.5, sector_pct: 25.0, next_tranche: 'N/A' },
  { symbol: 'NVDA', decision: 'ADD', confidence: 0.95, stability: 0.9, why: 'Strong growth fundamentals', why_not_add: null, expiry: '2026-08-02', portfolio_pct: 8.0, sector_pct: 25.0, next_tranche: 'Buy 50 shares' },
  { symbol: 'TSLA', decision: 'QUIT', confidence: 0.99, stability: 0.2, why: 'Price below 200 EMA', why_not_add: 'Thesis invalidated', expiry: '2026-08-02', portfolio_pct: 4.5, sector_pct: 15.0, next_tranche: 'Sell all' },
  { symbol: 'AMD', decision: 'STRUCTURE', confidence: 0.85, stability: 0.5, why: 'High overhead supply', why_not_add: 'Wait for resistance breakout', expiry: '2026-08-02', portfolio_pct: 5.0, sector_pct: 25.0, next_tranche: 'Hold/Trim' },
  { symbol: 'INTC', decision: 'ALERT', confidence: 0.8, stability: 0.4, why: 'Stability dropped recently', why_not_add: 'Watch closely before adding', expiry: '2026-08-02', portfolio_pct: 3.0, sector_pct: 25.0, next_tranche: 'N/A' }
];

export default function CaiV2Dashboard() {
  const [health, setHealth] = useState(MOCK_PORTFOLIO_HEALTH);
  const [holdings, setHoldings] = useState(MOCK_HOLDINGS);

  const getStateColor = (state: string) => {
    switch (state) {
      case 'ADD': return 'bg-green-100 text-green-800 border-green-300';
      case 'HOLD': return 'bg-gray-100 text-gray-800 border-gray-300';
      case 'ALERT': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'STRUCTURE': return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'QUIT': return 'bg-red-100 text-red-800 border-red-300';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen font-sans">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">CAI Decision Engine V2.1</h1>
      
      {/* Widgets Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-500 uppercase">Portfolio Health</h3>
          <p className="text-4xl font-bold text-gray-900 mt-2">{health.health_score.toFixed(1)} / 100</p>
          <p className="text-sm text-gray-400 mt-1">{health.total_positions} Total Positions</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 md:col-span-2">
          <h3 className="text-sm font-semibold text-gray-500 uppercase mb-4">Decision Distribution</h3>
          <div className="flex space-x-4">
            {Object.entries(health.state_distribution).map(([state, count]) => (
              <div key={state} className={`px-4 py-2 rounded border ${getStateColor(state)} flex-1 text-center`}>
                <div className="text-xs font-bold">{state}</div>
                <div className="text-2xl font-bold">{count}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Holdings Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-800">Holdings Ledger</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-100 text-gray-700 text-xs uppercase font-semibold">
              <tr>
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Decision</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Stability</th>
                <th className="px-4 py-3">Why</th>
                <th className="px-4 py-3">Why Not Add?</th>
                <th className="px-4 py-3">Next Tranche</th>
                <th className="px-4 py-3">Expiry</th>
                <th className="px-4 py-3">Port %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {holdings.map((h, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-bold text-gray-900">{h.symbol}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-bold border ${getStateColor(h.decision)}`}>
                      {h.decision}
                    </span>
                  </td>
                  <td className="px-4 py-3">{(h.confidence * 100).toFixed(0)}%</td>
                  <td className="px-4 py-3">{(h.stability * 100).toFixed(0)}%</td>
                  <td className="px-4 py-3 truncate max-w-xs" title={h.why}>{h.why}</td>
                  <td className="px-4 py-3 truncate max-w-xs text-gray-500 italic" title={h.why_not_add || ''}>
                    {h.why_not_add || '-'}
                  </td>
                  <td className="px-4 py-3 text-xs">{h.next_tranche}</td>
                  <td className="px-4 py-3 text-xs">{h.expiry}</td>
                  <td className="px-4 py-3">{h.portfolio_pct.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
