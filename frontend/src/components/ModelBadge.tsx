import { useState } from 'react';
import { MODEL_METADATA } from '../config/modelMetadata';
import { ModelIntelligencePanel } from './ModelIntelligencePanel';

export interface ModelResult {
  id: string;
  version?: string;
  status: string;
  score?: number;
  payload?: any;
  evaluation_date?: string;
}

export const ModelBadge = ({ result }: { result: ModelResult }) => {
  const [isOpen, setIsOpen] = useState(false);
  const meta = MODEL_METADATA[result.id] || {
    id: result.id,
    displayName: result.id,
    category: 'Unknown',
    getColor: () => 'bg-slate-800 text-slate-400 border-slate-700'
  };

  const colorClass = meta.getColor(result.status);

  return (
    <>
      <button 
        onClick={() => setIsOpen(true)}
        className={`px-2 py-1 text-xs font-semibold rounded border flex items-center gap-1.5 whitespace-nowrap cursor-pointer hover:brightness-110 transition-all ${colorClass}`} 
        title={`${meta.category} - ${meta.displayName}`}
      >
        <span>{meta.displayName}:</span>
        <span>{result.status}</span>
        <span className="text-[10px] ml-1 opacity-70">▼</span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 p-4 flex justify-between items-center z-10">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                {meta.displayName} Intelligence
              </h2>
              <button 
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                ✕
              </button>
            </div>
            <div className="p-4">
              <ModelIntelligencePanel models={[result]} />
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export const ModelBadgeGroup = ({ models }: { models?: ModelResult[] }) => {
  if (!models || models.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {models.map(m => (
        <ModelBadge key={m.id} result={m} />
      ))}
    </div>
  );
};
