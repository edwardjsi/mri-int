import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetch } from './api';

// Semantic decision colors from UX Spec
const STATE_COLORS = {
  ADD: '#10B981',
  MAINTAIN: '#3B82F6',
  ALERT: '#F59E0B',
  STRUCTURE: '#F97316',
  QUIT: '#EF4444'
} as const;

type DecisionState = keyof typeof STATE_COLORS;

export function StockDecisionPage() {
  const { decisionId: symbol } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch the real portfolio data and find the stock
    const fetchStockData = async () => {
      try {
        setLoading(true);
        const portfolio = await apiFetch('/cai/portfolio');
        const pos = portfolio.positions?.find((p: any) => p.symbol === symbol);
        
        if (pos) {
          const decision = (pos.decision || pos.cai_state || 'MAINTAIN') as DecisionState;
          setData({
            symbol: pos.symbol,
            currentPrice: pos.current_price || pos.average_price || 0,
            state: decision,
            lastEvaluated: new Date().toISOString(), // Mocking timestamp if missing
            allocation: {
              currentWeight: pos.allocation || 0,
              targetWeight: 12.0 // Still mocked as target weight usually comes from engine
            },
            narrative: {
              why: pos.cai_why || 'Waiting for CAI Engine weekly batch run.',
              whyNow: pos.cai_why_now || 'No immediate structural action triggered.',
              whatNext: pos.cai_what_next || 'Maintain position and wait for next signal.'
            },
            thresholds: [
              { level: 'Next Add', price: pos.next_add, type: 'ADD' },
              { level: 'Alert', price: pos.alert_level, type: 'ALERT' },
              { level: 'Structure', price: pos.structure_level, type: 'STRUCTURE' },
              { level: 'Quit', price: pos.quit_level, type: 'QUIT' }
            ]
          });
        } else {
          setData(null);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    if (symbol) {
      fetchStockData();
    }
  }, [symbol]);

  const formatPrice = (val: number | null | undefined) => val ? `₹${val.toFixed(2)}` : 'NOT_COMPUTED';
  
  if (loading) return <div className="p-8 text-center text-gray-500">Loading {symbol} Decision Context...</div>;
  if (!data) return <div className="p-8 text-center text-red-500">Could not find active position data for {symbol}</div>;

  const timestamp = new Date(data.lastEvaluated).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short'
  });

  const getStateStyle = (state: DecisionState) => ({
    backgroundColor: `${STATE_COLORS[state] || STATE_COLORS.MAINTAIN}20`,
    color: STATE_COLORS[state] || STATE_COLORS.MAINTAIN,
    borderColor: STATE_COLORS[state] || STATE_COLORS.MAINTAIN,
    borderWidth: '1px',
    borderStyle: 'solid'
  });

  // Calculate percentage placement for the current price marker on the ladder
  const validThresholds = data.thresholds.filter((t: any) => t.price != null);
  const maxPrice = Math.max(...validThresholds.map((t: any) => t.price), data.currentPrice);
  const minPrice = Math.min(...validThresholds.map((t: any) => t.price), data.currentPrice);
  
  const getTopPosition = (price: number) => {
    const range = maxPrice - minPrice;
    if (range === 0) return '50%';
    return `${((maxPrice - price) / range) * 100}%`;
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen font-sans" style={{ fontFamily: 'Inter, sans-serif' }}>
      
      {/* Header */}
      <div className="mb-6 flex justify-between items-end border-b border-gray-200 pb-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-4">
            {data.symbol}
            <span className="px-3 py-1 rounded text-sm font-bold tracking-wide uppercase" style={getStateStyle(data.state)}>
              {data.state}
            </span>
          </h1>
          <div className="text-2xl font-mono text-gray-700 mt-2 font-semibold">
            {formatPrice(data.currentPrice)}
          </div>
        </div>
        <div className="text-sm text-gray-500 text-right">
          <div>Last Evaluated</div>
          <div className="font-mono font-bold text-gray-700">{timestamp}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Pane: Context & Narrative */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Capital Allocation */}
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-4">Capital Allocation</h2>
            <div className="flex items-center gap-6">
              <div>
                <div className="text-xs text-gray-400">Current Weight</div>
                <div className="text-xl font-mono font-bold text-gray-800">{data.allocation.currentWeight.toFixed(1)}%</div>
              </div>
              <div className="text-gray-300 font-light text-3xl">/</div>
              <div>
                <div className="text-xs text-gray-400">Target Weight</div>
                <div className="text-xl font-mono font-bold text-gray-800">{data.allocation.targetWeight.toFixed(1)}%</div>
              </div>
              
              {/* Progress bar */}
              <div className="ml-8 flex-1 h-2 bg-gray-100 rounded overflow-hidden">
                <div 
                  className="h-full bg-blue-500 rounded" 
                  style={{ width: `${Math.min((data.allocation.currentWeight / data.allocation.targetWeight) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Narrative Block */}
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h2 className="text-sm font-semibold text-gray-500 uppercase mb-4">Decision Rationale</h2>
            <div className="space-y-6">
              
              <div className="p-4 bg-gray-50 border-l-4 border-gray-300 rounded-r">
                <h3 className="text-xs font-bold text-gray-500 uppercase mb-1">Why?</h3>
                <p className="text-gray-800 font-medium">{data.narrative.why}</p>
              </div>

              <div className="p-4 bg-gray-50 border-l-4 border-gray-300 rounded-r">
                <h3 className="text-xs font-bold text-gray-500 uppercase mb-1">Why Now?</h3>
                <p className="text-gray-800 font-medium">{data.narrative.whyNow}</p>
              </div>

              <div className="p-4 bg-blue-50 border-l-4 border-blue-400 rounded-r">
                <h3 className="text-xs font-bold text-blue-600 uppercase mb-1">What Next?</h3>
                <p className="text-gray-900 font-bold">{data.narrative.whatNext}</p>
              </div>

            </div>
          </div>
        </div>

        {/* Right Pane: Decision Ladder */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-6">Decision Ladder</h2>
          
          <div className="relative h-96 border-l-2 border-gray-200 ml-4 mt-8 mb-8" aria-label="Decision thresholds ladder">
            
            {/* Current Price Marker */}
            <div 
              className="absolute w-full flex items-center z-10 transition-all duration-300"
              style={{ top: getTopPosition(data.currentPrice), left: '-6px' }}
            >
              <div className="w-3 h-3 bg-gray-900 rounded-full border-2 border-white shadow"></div>
              <div className="ml-4 flex flex-col bg-gray-900 text-white px-3 py-1 rounded shadow-lg">
                <span className="text-[10px] uppercase font-bold text-gray-300 tracking-wider">Current</span>
                <span className="font-mono font-bold">{formatPrice(data.currentPrice)}</span>
              </div>
            </div>

            {/* Threshold Nodes */}
            {data.thresholds.map((threshold: any, idx: number) => {
              if (threshold.price == null) return null; // Don't plot missing thresholds on the ladder
              
              const stateType = threshold.type as DecisionState;
              return (
                <div 
                  key={idx} 
                  className="absolute w-full flex items-center"
                  style={{ top: getTopPosition(threshold.price), left: '-5px' }}
                >
                  <div 
                    className="w-2 h-2 rounded-full border-2 bg-white"
                    style={{ borderColor: STATE_COLORS[stateType] }}
                  ></div>
                  <div className="ml-6 flex flex-col">
                    <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: STATE_COLORS[stateType] }}>
                      {threshold.level}
                    </span>
                    <span className="font-mono text-gray-600 font-semibold">{formatPrice(threshold.price)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        
      </div>
    </div>
  );
}
