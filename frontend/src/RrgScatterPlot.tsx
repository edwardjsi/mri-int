import { useMemo } from 'react';

interface RrgScatterPlotProps {
  data: any[];
  onDotClick?: (symbol: string) => void;
}

export const RrgScatterPlot = ({ data, onDotClick }: RrgScatterPlotProps) => {
  const plotData = useMemo(() => {
    return data.filter((d: any) => d.rrg?.rs_ratio != null && d.rrg?.rs_momentum != null).map((d: any) => ({
      ...d,
      x: Number(d.rrg.rs_ratio),
      y: Number(d.rrg.rs_momentum),
    }));
  }, [data]);

  const { minX, maxX, minY, maxY } = useMemo(() => {
    if (plotData.length === 0) return { minX: 95, maxX: 105, minY: 95, maxY: 105 };
    let maxDiff = 5; // minimum spread
    plotData.forEach((d: any) => {
      maxDiff = Math.max(maxDiff, Math.abs(d.x - 100));
      maxDiff = Math.max(maxDiff, Math.abs(d.y - 100));
    });
    // Add 10% padding
    maxDiff *= 1.1;
    return {
      minX: 100 - maxDiff,
      maxX: 100 + maxDiff,
      minY: 100 - maxDiff,
      maxY: 100 + maxDiff
    };
  }, [plotData]);



  return (
    <div className="w-full aspect-square md:aspect-[2/1] relative bg-slate-900 border border-slate-700 rounded-lg overflow-hidden mb-6 select-none shadow-xl">
      {/* Quadrant Backgrounds */}
      <div className="absolute top-0 left-0 w-1/2 h-1/2 bg-amber-900/10 border-b border-r border-slate-700">
        <span className="absolute top-4 left-4 text-amber-500/50 font-bold uppercase tracking-widest">Improving</span>
      </div>
      <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-emerald-900/10 border-b border-slate-700">
        <span className="absolute top-4 right-4 text-emerald-500/50 font-bold uppercase tracking-widest">Leading</span>
      </div>
      <div className="absolute bottom-0 left-0 w-1/2 h-1/2 bg-rose-900/10 border-r border-slate-700">
        <span className="absolute bottom-4 left-4 text-rose-500/50 font-bold uppercase tracking-widest">Lagging</span>
      </div>
      <div className="absolute bottom-0 right-0 w-1/2 h-1/2 bg-orange-900/10">
        <span className="absolute bottom-4 right-4 text-orange-500/50 font-bold uppercase tracking-widest">Weakening</span>
      </div>

      {/* Axis Lines centered at 100, 100 */}
      <div className="absolute top-0 bottom-0 left-1/2 border-l-2 border-slate-600/50 -translate-x-1/2 z-0" />
      <div className="absolute left-0 right-0 top-1/2 border-t-2 border-slate-600/50 -translate-y-1/2 z-0" />

      {/* Dots */}
      <div className="absolute inset-0 z-10">
        {plotData.map((d: any) => {
          const leftPct = ((d.x - minX) / (maxX - minX)) * 100;
          // Y axis is inverted (higher momentum = top)
          const topPct = 100 - (((d.y - minY) / (maxY - minY)) * 100);

          let colorClass = "bg-slate-500";
          if (d.x > 100 && d.y > 100) colorClass = "bg-emerald-400";
          else if (d.x < 100 && d.y > 100) colorClass = "bg-amber-400";
          else if (d.x < 100 && d.y < 100) colorClass = "bg-rose-400";
          else if (d.x > 100 && d.y < 100) colorClass = "bg-orange-400";

          return (
            <div
              key={d.symbol}
              onClick={() => onDotClick && onDotClick(d.symbol)}
              className={`absolute w-3 h-3 -ml-1.5 -mt-1.5 rounded-full ${colorClass} shadow hover:scale-150 transition-transform cursor-pointer group`}
              style={{ left: `${leftPct}%`, top: `${topPct}%` }}
            >
              <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-slate-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-20 shadow-lg border border-slate-700">
                <div className="font-bold">{d.symbol}</div>
                <div>Ratio: {d.x.toFixed(2)}</div>
                <div>Mom: {d.y.toFixed(2)}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
