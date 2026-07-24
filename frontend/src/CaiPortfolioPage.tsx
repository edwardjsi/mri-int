import React, { useEffect, useState } from 'react';
import { getAuthHeaders } from './api';
import { CaiPositionReview } from './CaiPositionReview';
import { Briefcase, FileText, Database } from 'lucide-react';
import { CaiCommittee } from './CaiCommittee';
import { CaiLedger } from './CaiLedger';

export const CaiPortfolioPage: React.FC = () => {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewPositionId, setReviewPositionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'portfolio' | 'committee' | 'ledger'>('portfolio');

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/cai/portfolio', {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error('Failed to fetch CAI portfolio');
      const data = await res.json();
      setPortfolio(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  if (loading && !portfolio) {
    return <div className="p-8 text-center text-gray-400">Loading CAI Portfolio...</div>;
  }

  if (error) {
    return <div className="p-8 text-center text-red-500">{error}</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center">
            <Briefcase className="w-8 h-8 mr-3 text-blue-500" />
            CAI Portfolio Workspace
          </h1>
          <p className="text-gray-400 mt-2">Manage positions, monitor post-ownership health, and execute reviews.</p>
        </div>
        <div className="bg-gray-800 p-4 rounded-xl border border-gray-700 flex space-x-8">
          <div>
            <p className="text-sm text-gray-400">Available Cash</p>
            <p className="text-xl font-bold text-white">₹{portfolio?.cash?.toLocaleString() || '0'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-400">Avg Portfolio Health</p>
            <p className="text-xl font-bold text-green-500">{portfolio?.health ? `${portfolio.health}/100` : 'N/A'}</p>
          </div>
        </div>
      </div>

      <div className="flex space-x-4 border-b border-gray-800 pb-4">
        <button 
          onClick={() => setActiveTab('portfolio')}
          className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'portfolio' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800'}`}
        >
          <Briefcase className="w-4 h-4 mr-2" />
          Holdings
        </button>
        <button 
          onClick={() => setActiveTab('committee')}
          className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'committee' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800'}`}
        >
          <FileText className="w-4 h-4 mr-2" />
          Committee Report
        </button>
        <button 
          onClick={() => setActiveTab('ledger')}
          className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'ledger' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800'}`}
        >
          <Database className="w-4 h-4 mr-2" />
          Decision Ledger
        </button>
      </div>

      {activeTab === 'committee' && <CaiCommittee />}
      {activeTab === 'ledger' && <CaiLedger />}

      {activeTab === 'portfolio' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-800/50 border-b border-gray-800">
              <th className="p-4 text-gray-400 font-semibold">Symbol</th>
              <th className="p-4 text-gray-400 font-semibold text-right">Avg Price</th>
              <th className="p-4 text-gray-400 font-semibold text-right">Qty</th>
              <th className="p-4 text-gray-400 font-semibold text-center">Allocation</th>
              <th className="p-4 text-gray-400 font-semibold text-center">Tranches</th>
              <th className="p-4 text-gray-400 font-semibold text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {!portfolio?.positions || portfolio.positions.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-500">
                  No active positions found. Use Candidate Review in discovery screens to add your first tranche.
                </td>
              </tr>
            ) : (
              portfolio.positions.map((pos: any) => (
                <tr key={pos.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                  <td className="p-4 font-bold text-white">{pos.symbol}</td>
                  <td className="p-4 text-right font-mono text-gray-300">₹{pos.average_price.toFixed(2)}</td>
                  <td className="p-4 text-right text-gray-300">{pos.quantity}</td>
                  <td className="p-4 text-center">
                    <span className="bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full text-sm font-medium">
                      {pos.allocation}%
                    </span>
                  </td>
                  <td className="p-4 text-center">
                    <div className="flex justify-center space-x-1">
                      {Array.from({ length: 10 }).map((_, i) => (
                        <div 
                          key={i} 
                          className={`w-2 h-4 rounded-sm ${i < pos.tranche ? 'bg-green-500' : 'bg-gray-700'}`}
                        />
                      ))}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{pos.tranche}/10</p>
                  </td>
                  <td className="p-4 text-center">
                    <button 
                      onClick={() => setReviewPositionId(pos.id)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    >
                      Review
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      )}

      {reviewPositionId && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-2xl border border-gray-700 shadow-2xl">
            <CaiPositionReview 
              positionId={reviewPositionId} 
              onClose={() => setReviewPositionId(null)}
              onReviewSaved={() => {
                fetchPortfolio();
                setReviewPositionId(null);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
