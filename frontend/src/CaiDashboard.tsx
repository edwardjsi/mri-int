import React from 'react';
import { Briefcase, Activity, FileText, Database } from 'lucide-react';

export const CaiDashboard: React.FC<{ onNavigate: (page: string) => void }> = ({ onNavigate }) => {
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div className="text-center mb-10 mt-10">
        <h1 className="text-4xl font-bold text-white mb-4">Capital Allocation Intelligence (CAI)</h1>
        <p className="text-xl text-gray-400">Institutional Portfolio Management & Immutable Decision Ledgers</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div 
          onClick={() => onNavigate('caiportfolio')}
          className="bg-gray-900 border border-gray-800 p-6 rounded-2xl hover:border-blue-500 cursor-pointer transition-colors group"
        >
          <div className="bg-blue-500/10 w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-500/20">
            <Briefcase className="w-6 h-6 text-blue-500" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Portfolio Workspace</h3>
          <p className="text-gray-400 text-sm">Manage positions, monitor allocations, and view dynamic valuations.</p>
        </div>

        <div 
          onClick={() => onNavigate('caiportfolio')}
          className="bg-gray-900 border border-gray-800 p-6 rounded-2xl hover:border-purple-500 cursor-pointer transition-colors group"
        >
          <div className="bg-purple-500/10 w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:bg-purple-500/20">
            <Activity className="w-6 h-6 text-purple-500" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Position Reviews</h3>
          <p className="text-gray-400 text-sm">Post-ownership health checks based on weekly structural charts.</p>
        </div>

        <div 
          onClick={() => onNavigate('caiportfolio')}
          className="bg-gray-900 border border-gray-800 p-6 rounded-2xl hover:border-green-500 cursor-pointer transition-colors group"
        >
          <div className="bg-green-500/10 w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:bg-green-500/20">
            <FileText className="w-6 h-6 text-green-500" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Committee Reports</h3>
          <p className="text-gray-400 text-sm">Friday-batch reports consolidating all pending allocation decisions.</p>
        </div>

        <div 
          onClick={() => onNavigate('caiportfolio')}
          className="bg-gray-900 border border-gray-800 p-6 rounded-2xl hover:border-yellow-500 cursor-pointer transition-colors group"
        >
          <div className="bg-yellow-500/10 w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:bg-yellow-500/20">
            <Database className="w-6 h-6 text-yellow-500" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Decision Ledger</h3>
          <p className="text-gray-400 text-sm">Immutable execution logs and historical chart replay.</p>
        </div>
      </div>
    </div>
  );
};
