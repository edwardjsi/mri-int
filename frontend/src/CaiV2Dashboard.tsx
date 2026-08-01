import React, { useState, useMemo } from 'react';

// Semantic decision colors
const STATE_COLORS = {
  ADD: '#10B981',
  MAINTAIN: '#3B82F6',
  ALERT: '#F59E0B',
  STRUCTURE: '#F97316',
  QUIT: '#EF4444'
} as const;

type DecisionState = keyof typeof STATE_COLORS;

const STATE_PRIORITY: Record<DecisionState, number> = {
  QUIT: 1,
  STRUCTURE: 2,
  ALERT: 3,
  ADD: 4,
  MAINTAIN: 5
};

const MOCK_HOLDINGS = [
  { symbol: 'AAPL', decision: 'MAINTAIN' as DecisionState, price: 175.50, next_add: 180.00, alert: 170.00, structure: 165.00, quit: 155.00 },
  { symbol: 'NVDA', decision: 'ADD' as DecisionState, price: 450.25, next_add: null, alert: 420.00, structure: 400.00, quit: 380.00 },
  { symbol: 'TSLA', decision: 'QUIT' as DecisionState, price: 185.10, next_add: 250.00, alert: 210.00, structure: 200.00, quit: 190.00 },
  { symbol: 'AMD', decision: 'STRUCTURE' as DecisionState, price: 105.20, next_add: 120.00, alert: 110.00, structure: 108.00, quit: 95.00 },
  { symbol: 'INTC', decision: 'ALERT' as DecisionState, price: 34.50, next_add: 40.00, alert: 35.00, structure: 32.00, quit: 28.00 }
];

export default function CaiV2Dashboard() {
  const [holdings, setHoldings] = useState(MOCK_HOLDINGS);

  // Derive state distribution and actions today
  const distribution = useMemo(() => {
    const counts = { ADD: 0, MAINTAIN: 0, ALERT: 0, STRUCTURE: 0, QUIT: 0 };
    holdings.forEach(h => counts[h.decision]++);
    return counts;
  }, [holdings]);

  const actionsToday = holdings.filter(h => h.decision !== 'MAINTAIN');
  const sortedHoldings = useMemo(() => {
    return [...holdings].sort((a, b) => STATE_PRIORITY[a.decision] - STATE_PRIORITY[b.decision]);
  }, [holdings]);

  const getStateStyle = (state: DecisionState) => {
    return {
      backgroundColor: `${STATE_COLORS[state]}20`, // 20% opacity background
      color: STATE_COLORS[state],
      borderColor: STATE_COLORS[state],
      borderWidth: '1px',
      borderStyle: 'solid'
    };
  };

  const formatPrice = (val: number | null) => val ? `₹${val.toFixed(2)}` : '-';

  return (
    <div className="p-6 bg-gray-50 min-h-screen font-sans" style={{ fontFamily: 'Inter, sans-serif' }}>
      
      {/* Top Row: Hero */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-sm font-semibold text-gray-500 uppercase">Actions Today</h2>
          <div className="text-4xl font-bold text-gray-900 mt-2">{actionsToday.length} Actions</div>
          <div className="flex gap-2 mt-3">
            {['ADD', 'ALERT', 'STRUCTURE', 'QUIT'].map(state => {
              const count = distribution[state as DecisionState];
              if (count === 0) return null;
              return (
                <span key={state} className="px-2 py-1 rounded text-xs font-bold" style={getStateStyle(state as DecisionState)}>
                  {count} {state}
                </span>
              );
            })}
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 md:col-span-2 flex flex-col justify-center">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">Today's Priority Card</h2>
          {actionsToday.length > 0 ? (
            <div className="p-4 rounded border" style={getStateStyle(actionsToday[0].decision)}>
              <span className="font-bold text-lg">{actionsToday[0].symbol}</span> requires attention ({actionsToday[0].decision}). Review the decision ladder for next steps.
            </div>
          ) : (
            <div className="p-4 rounded border bg-green-50 text-green-800 border-green-200">
              No portfolio actions required today. All positions remain healthy. Next automated review: Friday Close.
            </div>
          )}
        </div>
      </div>

      {/* Middle Row: Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 md:col-span-2">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-4">Decision Distribution</h2>
          <div className="flex h-4 rounded overflow-hidden">
            {Object.entries(distribution).map(([state, count]) => {
              if (count === 0) return null;
              return (
                <div key={state} style={{ width: `${(count / holdings.length) * 100}%`, backgroundColor: STATE_COLORS[state as DecisionState] }} title={`${state}: ${count}`} />
              );
            })}
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-500 font-mono">
            {Object.entries(distribution).filter(([_, count]) => count > 0).map(([state, count]) => (
              <span key={state} style={{ color: STATE_COLORS[state as DecisionState] }} className="font-bold">{count} {state}</span>
            ))}
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-sm font-semibold text-gray-500 uppercase">Cash Available</h2>
          <div className="text-2xl font-mono font-bold text-gray-900 mt-2">₹1,250,000</div>
          <div className="text-xs text-gray-400 mt-1">Ready to deploy</div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex flex-col justify-center items-center">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2 w-full text-left">Market Regime</h2>
          <div className="px-4 py-2 bg-gray-100 text-gray-800 rounded-full font-bold text-sm border border-gray-300 w-full text-center">
            Bull Market
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
                <th className="px-4 py-3">Current Price</th>
                <th className="px-4 py-3">Next Add</th>
                <th className="px-4 py-3">Alert Level</th>
                <th className="px-4 py-3">Structure Level</th>
                <th className="px-4 py-3">Quit Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedHoldings.map((h, i) => {
                // Check if price is within 2% of alert level
                const isNearAlert = h.alert && Math.abs((h.price - h.alert) / h.alert) <= 0.02;
                return (
                  <tr key={i} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-bold text-gray-900 cursor-pointer text-blue-600 hover:underline">{h.symbol}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 rounded text-xs font-bold" style={getStateStyle(h.decision)}>
                        {h.decision}
                      </span>
                    </td>
                    <td className={`px-4 py-3 font-mono ${isNearAlert ? 'font-bold border-l-4 border-amber-500' : ''}`}>
                      {formatPrice(h.price)}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-500">{formatPrice(h.next_add)}</td>
                    <td className="px-4 py-3 font-mono text-amber-600">{formatPrice(h.alert)}</td>
                    <td className="px-4 py-3 font-mono text-orange-600">{formatPrice(h.structure)}</td>
                    <td className="px-4 py-3 font-mono text-red-600">{formatPrice(h.quit)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
