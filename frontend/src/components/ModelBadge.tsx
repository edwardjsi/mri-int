import { MODEL_METADATA } from '../config/modelMetadata';

interface ModelResult {
  id: string;
  version?: string;
  status: string;
  score?: number;
  payload?: any;
}

export const ModelBadge = ({ result }: { result: ModelResult }) => {
  const meta = MODEL_METADATA[result.id] || {
    id: result.id,
    displayName: result.id,
    category: 'Unknown',
    getColor: () => 'bg-slate-800 text-slate-400 border-slate-700'
  };

  const colorClass = meta.getColor(result.status);

  return (
    <div className={`px-2 py-1 text-xs font-semibold rounded border flex items-center gap-1.5 whitespace-nowrap ${colorClass}`} title={`${meta.category} - ${meta.displayName}`}>
      <span>{meta.displayName}:</span>
      <span>{result.status}</span>
    </div>
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
