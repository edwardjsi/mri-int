import React from 'react';

// Semantic decision colors from UX Spec
const STATE_COLORS = {
  ADD: '#10B981',
  MAINTAIN: '#3B82F6',
  ALERT: '#F59E0B',
  STRUCTURE: '#F97316',
  QUIT: '#EF4444'
} as const;

type DecisionState = keyof typeof STATE_COLORS;

interface Threshold {
  level: string;
  price: number;
  type: DecisionState;
}

interface FractalOverlayProps {
  thresholds: Threshold[];
  currentPrice: number;
  maxChartPrice: number; // For scaling
  minChartPrice: number; // For scaling
}

export default function FractalOverlay({ thresholds, currentPrice, maxChartPrice, minChartPrice }: FractalOverlayProps) {
  
  // Calculate top percentage based on the chart bounds
  const getTopPosition = (price: number) => {
    const range = maxChartPrice - minChartPrice;
    if (range <= 0) return '50%';
    const clampedPrice = Math.max(minChartPrice, Math.min(maxChartPrice, price));
    return `${((maxChartPrice - clampedPrice) / range) * 100}%`;
  };

  return (
    <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
      
      {/* Current Price Line */}
      <div 
        className="absolute w-full border-t border-dashed border-gray-900 z-20 flex justify-end"
        style={{ top: getTopPosition(currentPrice) }}
      >
        <div className="bg-gray-900 text-white text-[10px] font-mono font-bold px-2 py-0.5 rounded-l translate-y-[-50%] shadow">
          {currentPrice.toFixed(2)}
        </div>
      </div>

      {/* Threshold Overlays */}
      {thresholds.map((threshold, idx) => {
        const stateColor = STATE_COLORS[threshold.type];
        return (
          <div 
            key={idx} 
            className="absolute w-full border-t-2 z-10 opacity-70 flex"
            style={{ 
              top: getTopPosition(threshold.price), 
              borderColor: stateColor 
            }}
          >
            <div 
              className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest translate-y-[-100%]"
              style={{ backgroundColor: `${stateColor}20`, color: stateColor }}
            >
              {threshold.level}
            </div>
            <div className="flex-1" />
            <div 
              className="px-2 py-0.5 text-[10px] font-mono font-bold translate-y-[-50%] bg-white border"
              style={{ color: stateColor, borderColor: stateColor }}
            >
              {threshold.price.toFixed(2)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
