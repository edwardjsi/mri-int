import React, { useState } from 'react';
import { ModelResult } from './ModelBadge';

// --- Generic Components for Renderers ---

const EvidenceQuote = ({ quote, source }: { quote: string, source: string }) => (
  <div className="mt-1 text-xs text-slate-400 italic border-l-2 border-slate-600 pl-2 py-0.5 bg-slate-800/30">
    "{quote}" — <span className="text-slate-500">{source}</span>
  </div>
);

// --- Model Renderers ---

const CANSLIMRenderer = ({ model }: { model: ModelResult }) => {
  const [expanded, setExpanded] = useState(false);
  const payload = model.payload || {};
  const letters = payload.letters || [];

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
      {/* Summary Header */}
      <div 
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div>
          <h3 className="font-bold text-slate-100 flex items-center gap-2">
            CANSLIM
            <span className={`px-2 py-0.5 text-xs rounded font-semibold ${model.status === 'PASS' ? 'bg-emerald-900/50 text-emerald-400' : 'bg-rose-900/50 text-rose-400'}`}>
              {model.status}
            </span>
          </h3>
          <div className="text-sm text-slate-400 mt-1">
            Score: <span className="text-slate-200 font-medium">{model.score || 'N/A'}</span>/100
            <span className="mx-2">•</span>
            {payload.passed_count || 0} / 7 Passing
          </div>
        </div>
        <div className="text-slate-500">
          {expanded ? '▲' : '▼'}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="p-4 border-t border-slate-700 bg-slate-900/50">
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Evidence Breakdown</h4>
          <div className="space-y-4">
            {letters.map((l: any, i: number) => (
              <div key={i} className="flex gap-3 items-start">
                <div className={`flex-shrink-0 w-6 h-6 flex items-center justify-center rounded font-bold text-xs ${l.passed ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-500/30' : 'bg-rose-900/50 text-rose-400 border border-rose-500/30'}`}>
                  {l.letter}
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-200">
                    {l.title || l.letter}
                    <span className="ml-2 text-xs text-slate-500">{l.passed ? '✓' : '⚠'}</span>
                  </div>
                  {l.evidence && (
                    <div className="mt-1">
                      <EvidenceQuote quote={l.evidence.quote} source={l.evidence.source || 'Unknown'} />
                    </div>
                  )}
                </div>
              </div>
            ))}
            {letters.length === 0 && (
              <div className="text-sm text-slate-500 italic">No breakdown available.</div>
            )}
          </div>

          {/* History */}
          <div className="mt-6">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">History</h4>
            <div className="flex gap-1 text-xs">
              {(payload.history || []).map((h: any, i: number) => (
                <div key={i} className="flex flex-col items-center">
                  <div className="h-16 w-4 bg-slate-800 rounded-sm relative overflow-hidden">
                    <div className="absolute bottom-0 w-full bg-emerald-500/50" style={{ height: `${(h.score / 100) * 100}%` }}></div>
                  </div>
                  <span className="mt-1 text-slate-500 scale-75">{h.week || i}</span>
                </div>
              ))}
              {(!payload.history || payload.history.length === 0) && (
                <span className="text-slate-500 italic">No history available.</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const RRGRenderer = ({ model }: { model: ModelResult }) => {
  const [expanded, setExpanded] = useState(false);
  const payload = model.payload || {};

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
      <div 
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div>
          <h3 className="font-bold text-slate-100 flex items-center gap-2">
            RRG
            <span className={`px-2 py-0.5 text-xs rounded font-semibold ${model.status === 'LEADING' ? 'bg-emerald-900/50 text-emerald-400' : 'bg-amber-900/50 text-amber-400'}`}>
              {model.status}
            </span>
          </h3>
          <div className="text-sm text-slate-400 mt-1">
            Heading: <span className="text-slate-200 font-medium">{payload.heading || 'N/A'}°</span>
            <span className="mx-2">•</span>
            Benchmark: {payload.benchmark || 'NIFTY500'}
          </div>
        </div>
        <div className="text-slate-500">
          {expanded ? '▲' : '▼'}
        </div>
      </div>

      {expanded && (
        <div className="p-4 border-t border-slate-700 bg-slate-900/50">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Relative Strength Ratio</div>
              <div className="text-lg font-mono text-slate-200">{payload.rs_ratio || 'N/A'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Relative Momentum</div>
              <div className="text-lg font-mono text-slate-200">{payload.rs_momentum || 'N/A'}</div>
            </div>
          </div>

          {/* History */}
          <div className="mt-4 pt-4 border-t border-slate-800">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Quadrant History</h4>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              {(payload.history || []).map((h: any, i: number, arr: any[]) => (
                <React.Fragment key={i}>
                  <span className={h.status === 'LEADING' ? 'text-emerald-400 font-medium' : ''}>{h.status}</span>
                  {i < arr.length - 1 && <span className="text-slate-600">→</span>}
                </React.Fragment>
              ))}
              {(!payload.history || payload.history.length === 0) && (
                <span className="italic">No history available.</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const DefaultRenderer = ({ model }: { model: ModelResult }) => {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
      <div 
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-800 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div>
          <h3 className="font-bold text-slate-100">{model.id}</h3>
          <div className="text-sm text-slate-400 mt-1">Status: {model.status}</div>
        </div>
        <div className="text-slate-500">{expanded ? '▲' : '▼'}</div>
      </div>
      {expanded && (
        <div className="p-4 border-t border-slate-700 bg-slate-900/50">
          <pre className="text-xs text-slate-400 overflow-x-auto">
            {JSON.stringify(model.payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

// --- Registry ---

const MODEL_RENDERERS: Record<string, React.FC<{ model: ModelResult }>> = {
  CANSLIM: CANSLIMRenderer,
  RRG: RRGRenderer,
};

// --- Main Panel Component ---

export const ModelIntelligencePanel = ({ models }: { models?: ModelResult[] }) => {
  if (!models || models.length === 0) {
    return (
      <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-6 text-center">
        <div className="text-slate-400">No models have evaluated this company yet.</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {models.map(model => {
        const Renderer = MODEL_RENDERERS[model.id] || DefaultRenderer;
        return <Renderer key={`${model.id}-${model.version}`} model={model} />;
      })}
    </div>
  );
};
