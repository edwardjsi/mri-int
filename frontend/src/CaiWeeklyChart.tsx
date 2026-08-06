import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode, IChartApi, LineStyle } from 'lightweight-charts';
import { getAuthHeaders } from './api';

interface CaiWeeklyChartProps {
  symbol: string;
  positionData?: any;
}

export const CaiWeeklyChart: React.FC<CaiWeeklyChartProps> = ({ symbol, positionData }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          height: 1800,
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

        const candles = data.map((d: any) => ({
          time: d.time,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }));
        
        const ema10 = data.filter((d: any) => d.ema10 !== null).map((d: any) => ({
          time: d.time,
          value: d.ema10
        }));
        
        const ema40 = data.filter((d: any) => d.ema40 !== null).map((d: any) => ({
          time: d.time,
          value: d.ema40
        }));

        candlestickSeries.setData(candles);
        ema10Series.setData(ema10);
        ema40Series.setData(ema40);
        
        chart.timeScale().fitContent();

        if (positionData) {
          if (positionData.entry_price) {
            candlestickSeries.createPriceLine({
              price: positionData.entry_price,
              color: '#3B82F6', // MAINTAIN color (blue)
              lineWidth: 2,
              lineStyle: LineStyle.Dashed,
              axisLabelVisible: true,
              title: 'ENTRY (Avg Price)',
            });
          }
          if (positionData.add_level) {
            candlestickSeries.createPriceLine({
              price: positionData.add_level,
              color: '#10B981', // ADD color (green)
              lineWidth: 2,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: true,
              title: 'NEXT TRANCHE',
            });
          }
          if (positionData.pullback_level) {
            candlestickSeries.createPriceLine({
              price: positionData.pullback_level,
              color: '#8b5cf6', // Purple color for pullback
              lineWidth: 2,
              lineStyle: LineStyle.Dashed,
              axisLabelVisible: true,
              title: 'PULLBACK ENTRY',
            });
          }
          if (positionData.alert_level) {
            candlestickSeries.createPriceLine({
              price: positionData.alert_level,
              color: '#F59E0B', // ALERT color (yellow)
              lineWidth: 2,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: true,
              title: 'ALERT',
            });
          }
          if (positionData.structure_level) {
            candlestickSeries.createPriceLine({
              price: positionData.structure_level,
              color: '#F97316', // STRUCTURE color (orange)
              lineWidth: 2,
              lineStyle: LineStyle.Solid,
              axisLabelVisible: true,
              title: 'STRUCTURE BREAK',
            });
          }
          if (positionData.quit_level) {
            candlestickSeries.createPriceLine({
              price: positionData.quit_level,
              color: '#EF4444', // QUIT color (red)
              lineWidth: 2,
              lineStyle: LineStyle.Solid,
              axisLabelVisible: true,
              title: 'QUIT',
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
    <div className="relative w-full h-[400px] bg-gray-900 rounded-lg overflow-hidden border border-gray-800">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 z-10">
          <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
        </div>
      )}
      <div ref={chartContainerRef} className="w-full h-full" />
      {positionData && (
        <div className="absolute top-4 left-4 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg p-3 text-xs font-mono text-gray-300 z-20 pointer-events-auto shadow-xl select-text">
          <div className="text-gray-400 font-bold mb-2 border-b border-gray-700 pb-1 tracking-wider uppercase">Key Levels (Selectable)</div>
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
  );
};
