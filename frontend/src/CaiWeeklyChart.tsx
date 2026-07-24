import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode, IChartApi } from 'lightweight-charts';
import { getAuthHeaders } from './api';

interface CaiWeeklyChartProps {
  symbol: string;
}

export const CaiWeeklyChart: React.FC<CaiWeeklyChartProps> = ({ symbol }) => {
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
          height: 400,
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
    </div>
  );
};
