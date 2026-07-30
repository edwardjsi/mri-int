import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

const Accordion = ({ title, children, defaultOpen = false }: any) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-700 rounded-lg mb-4 bg-gray-800 overflow-hidden">
      <button 
        className="w-full flex justify-between items-center p-4 text-white hover:bg-gray-700/50 transition"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="font-medium">{title}</span>
        {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {isOpen && (
        <div className="p-4 border-t border-gray-700 text-gray-300 text-sm bg-gray-800/50">
          {children}
        </div>
      )}
    </div>
  );
};

export const StockDecisionPanel = ({ holding, onClose }: any) => {
  if (!holding) return null;
  
  const tree = holding.explanation_tree;

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-[450px] bg-gray-900 border-l border-gray-700 shadow-2xl transform transition-transform duration-300 ease-in-out z-50 overflow-y-auto flex flex-col">
      <div className="p-6 border-b border-gray-800 flex justify-between items-center sticky top-0 bg-gray-900 z-10">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          {holding.ticker} Decision
        </h3>
        <button onClick={onClose} className="text-gray-400 hover:text-white transition text-2xl leading-none">&times;</button>
      </div>
      
      <div className="p-6 flex-grow">
        {!tree ? (
          <div className="bg-red-900/30 p-4 rounded text-red-400 border border-red-800">
            Error: Explanation tree is missing or invalid for this recommendation.
          </div>
        ) : (
          <>
            <Accordion title="Recommendation" defaultOpen={true}>
              <div className="space-y-2">
                <div className="flex justify-between border-b border-gray-700 pb-2">
                  <span className="text-gray-400">Action</span>
                  <span className="font-bold text-white">{holding.current_action}</span>
                </div>
                <div className="flex justify-between border-b border-gray-700 pb-2">
                  <span className="text-gray-400">Confidence</span>
                  <span className="font-bold text-white">{holding.confidence}%</span>
                </div>
                <div className="pt-1">
                  <span className="text-gray-400 block mb-1">Summary</span>
                  <span>{holding.primary_reason}</span>
                </div>
              </div>
            </Accordion>
            
            <Accordion title="Why" defaultOpen={true}>
              <div className="space-y-3">
                <div>
                  <span className="text-gray-400 block mb-1">Primary Reason</span>
                  <p>{holding.primary_reason}</p>
                </div>
                {holding.secondary_reason && (
                  <div>
                    <span className="text-gray-400 block mb-1">Supporting Context</span>
                    <p>{holding.secondary_reason}</p>
                  </div>
                )}
              </div>
            </Accordion>
            
            <Accordion title="Rules">
              <div className="space-y-3">
                {tree.children && tree.children.length > 0 ? (
                  tree.children.map((child: any, idx: number) => (
                     <div key={idx} className="bg-gray-900 p-3 rounded border border-gray-700">
                       <div className="font-semibold text-white mb-1">{child.name}</div>
                       <div className="text-xs text-gray-400">Result: <span className="text-gray-200">{child.result}</span></div>
                       {child.details && Object.entries(child.details).map(([k, v]) => (
                         <div key={k} className="text-xs text-gray-400 mt-1">
                           <span className="capitalize">{k.replace('_', ' ')}</span>: {String(v)}
                         </div>
                       ))}
                     </div>
                  ))
                ) : (
                  <p className="text-gray-500">No rule evaluations found.</p>
                )}
              </div>
            </Accordion>
            
            <Accordion title="Evidence">
              <div className="space-y-2">
                {holding.supporting_evidence && holding.supporting_evidence.length > 0 ? (
                  <ul className="list-disc pl-4 space-y-1">
                    {holding.supporting_evidence.map((ev: string, i: number) => (
                      <li key={i}>{ev}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500">No supporting evidence provided.</p>
                )}
                
                {tree.details && tree.details.calculations && (
                  <div className="mt-4 border-t border-gray-700 pt-3">
                    <h4 className="text-gray-400 mb-2 font-medium">Calculations</h4>
                    {tree.details.calculations.map((calc: any, i: number) => (
                       <div key={i} className="bg-gray-900 p-2 rounded text-xs border border-gray-700">
                         <div><strong>{calc.name}</strong></div>
                         <div>Formula: {calc.formula}</div>
                         <div>Inputs: {calc.inputs}</div>
                         <div>Output: {calc.output}</div>
                       </div>
                    ))}
                  </div>
                )}
              </div>
            </Accordion>
          </>
        )}
      </div>
    </div>
  );
};
