import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode, IChartApi, LineStyle } from 'lightweight-charts';
import { getAuthHeaders } from './api';

interface CaiWeeklyChartProps {
  symbol: string;
  positionData?: any;
  caiConfig?: any;
}

export const CaiWeeklyChart: React.FC<CaiWeeklyChartProps> = ({ symbol, positionData, caiConfig }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showMriLevels, setShowMriLevels] = useState(false);
  const [latestDate, setLatestDate] = useState<string | null>(null);

  useEffect(() => {
    let chart: IChartApi | null = null;
    
    const fetchAndRender = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/portfolio-review/chart/${symbol}`, {
          headers: getAuthHeaders(),
        });
        
        if (!res.ok) {
          throw new Error('Failed to fetch chart data');
        }
        
        const json = await res.json();
        const data = json.data;

        if (!chartContainerRef.current) return;
        
        chart = createChart(chartContainerRef.current, {
          layout: {
            background: { type: ColorType.Solid, color: '#111827' },
            textColor: '#d1d5db',
          },
          grid: {
            vertLines: { color: '#374151' },
            horzLines: { color: '#374151' },
          },
          crosshair: {
            mode: CrosshairMode.Normal,
          },
          width: chartContainerRef.current.clientWidth,
          height: 900,
          timeScale: {
            timeVisible: true,
            borderColor: '#374151',
          },
          rightPriceScale: {
            borderColor: '#374151',
          }
        });

        const candlestickSeries = chart.addCandlestickSeries({
          upColor: '#10b981',
          downColor: '#ef4444',
          borderVisible: false,
          wickUpColor: '#10b981',
          wickDownColor: '#ef4444',
        });

        const ema10Series = chart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 2,
          title: 'EMA 10',
        });

        const ema40Series = chart.addLineSeries({
          color: '#8b5cf6',
          lineWidth: 2,
          title: 'EMA 40',
        });

        const formatTime = (t: any) => {
          if (typeof t === 'string') return t.split('T')[0];
          if (typeof t === 'number' && t > 9999999999) return Math.floor(t / 1000);
          return t;
        };

        const candles = data.map((d: any) => ({
          time: formatTime(d.time),
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }));

        if (candles.length > 0) {
          setLatestDate(candles[candles.length - 1].time);
        }
        
        const ema10 = data.filter((d: any) => d.ema10 !== null).map((d: any) => ({
          time: formatTime(d.time),
          value: d.ema10
        }));
        
        const ema40 = data.filter((d: any) => d.ema40 !== null).map((d: any) => ({
          time: formatTime(d.time),
          value: d.ema40
        }));

        candlestickSeries.setData(candles);
        ema10Series.setData(ema10);
        ema40Series.setData(ema40);
        
        chart.timeScale().fitContent();

        if (positionData && showMriLevels) {
          if (positionData.entry_price) {
            candlestickSeries.createPriceLine({
              price: positionData.entry_price,
              color: '#3B82F6',
              lineWidth: 1,
              lineStyle: LineStyle.Dashed,
              axisLabelVisible: true,
              title: 'ENTRY',
            });
          }
          if (positionData.add_level) {
            candlestickSeries.createPriceLine({
              price: positionData.add_level,
              color: '#10B981',
              lineWidth: 1,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: true,
              title: 'NEXT TRANCHE',
            });
          }
          if (positionData.pullback_level) {
            candlestickSeries.createPriceLine({
              price: positionData.pullback_level,
              color: '#8b5cf6',
              lineWidth: 1,
              lineStyle: LineStyle.Dashed,
              axisLabelVisible: true,
              title: 'PULLBACK ENTRY',
            });
          }
          if (positionData.alert_level) {
            candlestickSeries.createPriceLine({
              price: positionData.alert_level,
              color: '#F59E0B',
              lineWidth: 1,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: true,
              title: 'ALERT',
            });
          }
          if (positionData.structure_level) {
            candlestickSeries.createPriceLine({
              price: positionData.structure_level,
              color: '#F97316',
              lineWidth: 1,
              lineStyle: LineStyle.Solid,
              axisLabelVisible: true,
              title: 'STRUCTURE BREAK',
            });
          }
          if (positionData.quit_level) {
            candlestickSeries.createPriceLine({
              price: positionData.quit_level,
              color: '#EF4444',
              lineWidth: 1,
              lineStyle: LineStyle.Solid,
              axisLabelVisible: true,
              title: 'QUIT',
            });
          }
        }
        
        if (caiConfig) {
          if (caiConfig.pullback_upper_bound) {
            candlestickSeries.createPriceLine({
              price: caiConfig.pullback_upper_bound,
              color: '#22c55e',
              lineWidth: 2,
              lineStyle: LineStyle.Solid,
              axisLabelVisible: true,
              title: `PULLBACK ZONE HIGH ${caiConfig.pullback_upper_bound}`,
            });
            if (caiConfig.pullback_lower_bound) {
               candlestickSeries.createPriceLine({
                 price: caiConfig.pullback_lower_bound,
                 color: '#22c55e',
                 lineWidth: 2,
                 lineStyle: LineStyle.Solid,
                 axisLabelVisible: true,
                 title: `PULLBACK ZONE LOW ${caiConfig.pullback_lower_bound}`,
               });
            }
          }
          
          if (caiConfig.breakout_confirmation_price) {
            const bcLine = {
              price: caiConfig.breakout_confirmation_price,
              color: '#3b82f6',
              lineWidth: 2 as const,
              lineStyle: LineStyle.Solid,
              axisLabelVisible: true,
              title: `BREAKOUT ${caiConfig.breakout_confirmation_price}`,
            };
            candlestickSeries.createPriceLine(bcLine);
          }
          
          if (caiConfig.next_add_price) {
            const naLine = {
              price: caiConfig.next_add_price,
              color: '#a855f7',
              lineWidth: 2 as const,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: true,
              title: `NEXT ADD ${caiConfig.next_add_price}`,
            };
            candlestickSeries.createPriceLine(naLine);
          }
          
          if (caiConfig.structural_break_price) {
            candlestickSeries.createPriceLine({
              price: caiConfig.structural_break_price,
              color: '#ef4444',
              lineWidth: 3,
              lineStyle: LineStyle.Solid,
              axisLabelVisible: true,
              title: `STRUCTURE ${caiConfig.structural_break_price}`,
            });
          }
        }
        
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchAndRender();

    const handleResize = () => {
      if (chart && chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chart) {
        chart.remove();
      }
    };
  }, [symbol]);

  if (error) {
    return <div className="p-4 text-red-500 bg-red-500/10 rounded-lg">{error}</div>;
  }

  return (
    <div className="flex flex-col space-y-2 relative w-full h-[600px] md:h-[700px]">
      <div className="absolute top-4 right-4 z-10 flex items-center gap-4">
        {latestDate && (
          <div className="px-3 py-1.5 bg-gray-800/80 rounded border border-gray-700 text-sm text-gray-300 font-medium">
            Reviewing Week: {latestDate}
          </div>
        )}
        <button 
          onClick={() => setShowMriLevels(!showMriLevels)}
          className={`px-3 py-1 text-xs rounded border transition-colors ${showMriLevels ? 'bg-gray-700 text-white border-gray-600' : 'bg-transparent text-gray-400 border-gray-700 hover:text-gray-300'}`}
        >
          {showMriLevels ? 'Hide MRI Technical Levels' : 'Show MRI Technical Levels'}
        </button>
      </div>
      <div className="relative w-full h-[400px] md:h-[600px] bg-gray-900 rounded-lg overflow-hidden border border-gray-800">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 z-10">
            <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-full" />
        {positionData && (showMriLevels || !caiConfig) && (
          <div className="absolute top-4 left-4 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg p-3 text-xs font-mono text-gray-300 z-20 pointer-events-auto shadow-xl select-text">
            <div className="text-gray-400 font-bold mb-2 border-b border-gray-700 pb-1 tracking-wider uppercase">MRI Levels</div>
            <div className="flex flex-col gap-1.5">
              {positionData.entry_price && <div><span className="text-blue-400 inline-block w-24">ENTRY:</span> {positionData.entry_price.toFixed(2)}</div>}
              {positionData.add_level && <div><span className="text-emerald-400 inline-block w-24">NEXT TRANCHE:</span> {positionData.add_level.toFixed(2)}</div>}
              {positionData.pullback_level && <div><span className="text-purple-400 inline-block w-24">PULLBACK:</span> {positionData.pullback_level.toFixed(2)}</div>}
              {positionData.alert_level && <div><span className="text-yellow-400 inline-block w-24">ALERT:</span> {positionData.alert_level.toFixed(2)}</div>}
              {positionData.structure_level && <div><span className="text-orange-400 inline-block w-24">STRUCTURE:</span> {positionData.structure_level.toFixed(2)}</div>}
              {positionData.quit_level && <div><span className="text-red-400 inline-block w-24">QUIT:</span> {positionData.quit_level.toFixed(2)}</div>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
