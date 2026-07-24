import React, { useEffect, useState } from 'react';
import { getAuthHeaders } from './api';
import { Database, PlayCircle } from 'lucide-react';

export const CaiLedger: React.FC = () => {
  const [ledger, setLedger] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);

  const fetchLedger = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/portfolio-review/ledger', {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error('Failed to fetch ledger');
      const data = await res.json();
      setLedger(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, []);

  const handleExecute = async () => {
    try {
      setExecuting(true);
      const res = await fetch('/api/portfolio-review/ledger/execute', {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to execute ledger');
      alert(`Successfully executed ${data.executed} pending decisions.`);
      fetchLedger();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setExecuting(false);
    }
  };

  const pendingCount = ledger.filter(l => l.execution_status === 'PENDING').length;

  return (
    <div className="p-6 bg-gray-900 border border-gray-800 rounded-xl space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center">
            <Database className="w-6 h-6 mr-2 text-indigo-500" />
            Decision Ledger
          </h2>
          <p className="text-gray-400 mt-1">Immutable audit trail of committee decisions.</p>
        </div>
        
        <button
          onClick={handleExecute}
          disabled={executing || pendingCount === 0}
          className={`flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${
            pendingCount > 0 
              ? 'bg-blue-600 hover:bg-blue-500 text-white' 
              : 'bg-gray-800 text-gray-500 cursor-not-allowed'
          }`}
        >
          <PlayCircle className="w-5 h-5 mr-2" />
          {executing ? 'Executing...' : `Execute Pending (${pendingCount})`}
        </button>
      </div>

      {error && <div className="p-4 bg-red-500/10 text-red-500 border border-red-500/20 rounded-lg">{error}</div>}

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-800/50 border-b border-gray-700">
              <th className="p-4 text-gray-400 font-semibold">Date</th>
              <th className="p-4 text-gray-400 font-semibold">Symbol</th>
              <th className="p-4 text-gray-400 font-semibold">Decision</th>
              <th className="p-4 text-gray-400 font-semibold">Reason</th>
              <th className="p-4 text-gray-400 font-semibold">Status</th>
              <th className="p-4 text-gray-400 font-semibold text-right">Exec Price</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-500">Loading ledger...</td>
              </tr>
            ) : ledger.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-500">No ledger entries found.</td>
              </tr>
            ) : (
              ledger.map((entry: any, idx: number) => (
                <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/30">
                  <td className="p-4 text-gray-400 whitespace-nowrap">
                    {entry.execution_date ? new Date(entry.execution_date).toLocaleDateString() : '-'}
                  </td>
                  <td className="p-4 font-bold text-white">{entry.symbol}</td>
                  <td className="p-4">
                    <span className="bg-gray-800 px-2 py-1 rounded text-gray-300 font-medium text-xs">
                      {entry.recommendation}
                    </span>
                  </td>
                  <td className="p-4 text-gray-400 text-sm max-w-xs truncate" title={entry.reason}>
                    {entry.reason}
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      entry.execution_status === 'EXECUTED' ? 'bg-green-500/20 text-green-500' :
                      entry.execution_status === 'PENDING' ? 'bg-yellow-500/20 text-yellow-500' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {entry.execution_status}
                    </span>
                  </td>
                  <td className="p-4 text-right font-mono text-gray-300">
                    {entry.execution_price ? `₹${Number(entry.execution_price).toFixed(2)}` : '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
