import React, { useEffect, useState } from 'react';
import { apiFetch } from './api';
import { CaiPositionReview } from './CaiPositionReview';
import { Briefcase, FileText, Database, ArrowUpDown } from 'lucide-react';
import { CaiCommittee } from './CaiCommittee';
import { CaiLedger } from './CaiLedger';

export const CaiPortfolioPage: React.FC = () => {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewPositionId, setReviewPositionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'portfolio' | 'committee' | 'ledger'>('portfolio');
  const [showManualTrade, setShowManualTrade] = useState(false);
  const [tradeType, setTradeType] = useState<'NEW' | 'TRANCHE'>('NEW');
  const [tradeSymbol, setTradeSymbol] = useState('');
  const [tradeQty, setTradeQty] = useState('');
  const [tradePrice, setTradePrice] = useState('');
  const [tradePosId, setTradePosId] = useState('');

  const [sortField, setSortField] = useState<string>('symbol');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const handleManualTrade = async () => {
    try {
      if (tradeType === 'NEW') {
        await apiFetch('/cai/portfolio/positions', {
          method: 'POST',
          body: JSON.stringify({ symbol: tradeSymbol, quantity: Number(tradeQty), average_price: Number(tradePrice) })
        });
      } else {
        await apiFetch(`/cai/portfolio/positions/${tradePosId}/tranches`, {
          method: 'POST',
          body: JSON.stringify({ quantity: Number(tradeQty), entry_price: Number(tradePrice) })
        });
      }
      setShowManualTrade(false);
      setTradeSymbol(''); setTradeQty(''); setTradePrice(''); setTradePosId('');
      fetchPortfolio();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      const data = await apiFetch('/cai/portfolio');
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

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedPositions = portfolio?.positions ? [...portfolio.positions].sort((a: any, b: any) => {
    let aVal = a[sortField];
    let bVal = b[sortField];
    
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }
    
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  }) : [];

  const totalInvested = portfolio?.positions?.reduce((sum: number, pos: any) => sum + (pos.quantity * pos.average_price), 0) || 0;

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
          <div className="flex justify-between items-center p-4 border-b border-gray-800 bg-gray-800/20">
            <h2 className="text-lg font-bold text-white">Active Positions</h2>
            <button 
              onClick={() => setShowManualTrade(true)}
              className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              + Manual Trade Entry
            </button>
          </div>
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-800/50 border-b border-gray-800">
              <th className="p-4 text-gray-400 font-semibold cursor-pointer hover:text-white" onClick={() => handleSort('symbol')}>
                <div className="flex items-center">Symbol <ArrowUpDown className="w-3 h-3 ml-2 opacity-50"/></div>
              </th>
              <th className="p-4 text-gray-400 font-semibold text-right cursor-pointer hover:text-white" onClick={() => handleSort('average_price')}>
                <div className="flex items-center justify-end">Avg Price <ArrowUpDown className="w-3 h-3 ml-2 opacity-50"/></div>
              </th>
              <th className="p-4 text-gray-400 font-semibold text-right cursor-pointer hover:text-white" onClick={() => handleSort('quantity')}>
                <div className="flex items-center justify-end">Qty <ArrowUpDown className="w-3 h-3 ml-2 opacity-50"/></div>
              </th>
              <th className="p-4 text-gray-400 font-semibold text-center cursor-pointer hover:text-white" onClick={() => handleSort('allocation')}>
                <div className="flex items-center justify-center">Allocation <ArrowUpDown className="w-3 h-3 ml-2 opacity-50"/></div>
              </th>
              <th className="p-4 text-gray-400 font-semibold text-center cursor-pointer hover:text-white" onClick={() => handleSort('tranche')}>
                <div className="flex items-center justify-center">Tranches <ArrowUpDown className="w-3 h-3 ml-2 opacity-50"/></div>
              </th>
              <th className="p-4 text-gray-400 font-semibold text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {!sortedPositions || sortedPositions.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-500">
                  No active positions found. Use Candidate Review in discovery screens to add your first tranche.
                </td>
              </tr>
            ) : (
              sortedPositions.map((pos: any) => (
                <tr key={pos.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                  <td className="p-4 font-bold text-white">{pos.symbol}</td>
                  <td className="p-4 text-right font-mono text-gray-300">₹{pos.average_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
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
          {sortedPositions && sortedPositions.length > 0 && (
            <tfoot className="bg-gray-800/80 border-t-2 border-gray-700">
              <tr>
                <td className="p-4 font-bold text-white">Total</td>
                <td className="p-4 text-right font-mono font-bold text-blue-400">
                  ₹{totalInvested.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </td>
                <td colSpan={4}></td>
              </tr>
            </tfoot>
          )}
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
      {showManualTrade && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 w-full max-w-md p-6 rounded-2xl border border-gray-700 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Manual Trade Entry</h3>
            
            <div className="flex gap-4 mb-4">
              <label className="flex items-center text-gray-300">
                <input type="radio" checked={tradeType === 'NEW'} onChange={() => setTradeType('NEW')} className="mr-2" />
                New Position
              </label>
              <label className="flex items-center text-gray-300">
                <input type="radio" checked={tradeType === 'TRANCHE'} onChange={() => setTradeType('TRANCHE')} className="mr-2" />
                Add Tranche
              </label>
            </div>

            {tradeType === 'NEW' && (
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Symbol</label>
                <input type="text" className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white" value={tradeSymbol} onChange={e => setTradeSymbol(e.target.value.toUpperCase())} placeholder="e.g. LENSKART" />
              </div>
            )}

            {tradeType === 'TRANCHE' && (
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Select Position</label>
                <select className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white" value={tradePosId} onChange={e => setTradePosId(e.target.value)}>
                  <option value="">-- Select Active Position --</option>
                  {portfolio?.positions?.map((p: any) => (
                    <option key={p.id} value={p.id}>{p.symbol} (Tranche {p.tranche}/10)</option>
                  ))}
                </select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Quantity</label>
                <input type="number" className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white" value={tradeQty} onChange={e => setTradeQty(e.target.value)} />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Price (₹)</label>
                <input type="number" className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white" value={tradePrice} onChange={e => setTradePrice(e.target.value)} />
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <button className="px-4 py-2 text-gray-400 hover:text-white" onClick={() => setShowManualTrade(false)}>Cancel</button>
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium" onClick={handleManualTrade}>
                Execute Trade
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
