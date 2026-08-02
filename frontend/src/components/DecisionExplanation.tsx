import React, { useState } from 'react';

// The canonical ExplainNode matching the backend Pydantic model
export interface ExplainNodeData {
  type: 'DECISION' | 'RULE' | 'OBSERVATION' | 'FACT';
  id: string;
  status?: string;
  title?: string;
  quote?: string;
  children?: ExplainNodeData[];
}

export interface ExplainTreeData {
  model: string;
  result: string;
  children: ExplainNodeData[];
}

const NodeIcon = ({ type }: { type: string }) => {
  switch (type) {
    case 'DECISION': return <span className="text-purple-400">⚡</span>;
    case 'RULE': return <span className="text-blue-400">⚖️</span>;
    case 'OBSERVATION': return <span className="text-emerald-400">👁️</span>;
    case 'FACT': return <span className="text-amber-400">📄</span>;
    default: return <span className="text-gray-400">▪️</span>;
  }
};

const ExplainNode: React.FC<{ node: ExplainNodeData; level: number }> = ({ node, level }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;
  
  const getStatusColor = (status?: string) => {
    if (status === 'PASS') return 'text-emerald-400 font-bold';
    if (status === 'FAIL') return 'text-red-400 font-bold';
    return 'text-gray-300';
  };

  return (
    <div className="flex flex-col mb-1" style={{ marginLeft: `${level * 1.5}rem` }}>
      <div 
        className={`flex items-start p-2 rounded border border-slate-700/50 bg-slate-800/50 hover:bg-slate-700/80 transition-colors ${hasChildren ? 'cursor-pointer' : ''}`}
        onClick={() => hasChildren && setIsExpanded(!isExpanded)}
      >
        <div className="mr-3 mt-0.5 w-5 h-5 flex items-center justify-center">
          {hasChildren ? (
            <span className="text-slate-400 text-xs">{isExpanded ? '▼' : '▶'}</span>
          ) : (
            <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
          )}
        </div>
        
        <div className="mr-3 mt-0.5">
          <NodeIcon type={node.type} />
        </div>
        
        <div className="flex-1 flex flex-col">
          <div className="flex justify-between items-center">
            <div className="flex gap-2 items-baseline">
              <span className="text-xs text-slate-400 tracking-wider font-mono uppercase">{node.type}</span>
              <span className="text-sm font-mono text-slate-200">{node.id}</span>
            </div>
            {node.status && (
              <span className={`text-sm ${getStatusColor(node.status)}`}>{node.status}</span>
            )}
          </div>
          
          {node.title && <div className="text-sm text-slate-300 mt-1">{node.title}</div>}
          
          {node.quote && (
            <div className="mt-2 text-sm text-slate-400 italic border-l-2 border-slate-600 pl-3 py-1">
              "{node.quote}"
            </div>
          )}
        </div>
      </div>

      {hasChildren && isExpanded && (
        <div className="mt-2 flex flex-col gap-2 relative">
          {/* Vertical connecting line */}
          <div className="absolute left-6 top-0 bottom-4 w-px bg-slate-700/50 -z-10" />
          
          {node.children!.map((child, idx) => (
            <ExplainNode key={`${child.id}-${idx}`} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export const DecisionExplanation: React.FC<{ tree: ExplainTreeData }> = ({ tree }) => {
  return (
    <div className="w-full max-w-4xl mx-auto rounded-lg bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden font-sans">
      <div className="px-6 py-4 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <span className="text-purple-400">⚡</span>
            {tree.model} Decision Trace
          </h2>
          <p className="text-xs text-slate-400 mt-1">Universal Explainability Framework</p>
        </div>
        <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
          <span className="text-xs text-slate-400 uppercase tracking-widest">Verdict</span>
          <span className={`font-bold ${tree.result === 'PASS' || tree.result === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>
            {tree.result}
          </span>
        </div>
      </div>
      
      <div className="p-6 bg-slate-900/50">
        <div className="flex flex-col gap-2">
          {tree.children.map((child, idx) => (
            <ExplainNode key={`${child.id}-${idx}`} node={child} level={0} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default DecisionExplanation;
