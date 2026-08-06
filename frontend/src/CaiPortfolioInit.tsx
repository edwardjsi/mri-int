import React, { useState } from 'react';
import { apiFetch } from './api';
import { Upload } from 'lucide-react';

export const CaiPortfolioInit: React.FC = () => {
  const [csvData, setCsvData] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleImport = async () => {
    try {
      setLoading(true);
      setResult(null);
      // Basic CSV parsing
      const lines = csvData.trim().split('\n');
      const events = lines.slice(1).map(line => {
        const [symbol, date, quantity, price, allocation_reason] = line.split(',');
        return {
          symbol: symbol.trim(),
          date: date.trim(),
          quantity: parseInt(quantity.trim()),
          price: parseFloat(price.trim()),
          allocation_reason: allocation_reason.trim()
        };
      });

      const res = await apiFetch('/cai/portfolio/init-ledger', {
        method: 'POST',
        body: JSON.stringify({ events })
      });
      setResult(res);
    } catch (err: any) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto h-full flex flex-col space-y-6">
      <h2 className="text-2xl font-bold text-white">Initialize Capital Allocation Ledger</h2>
      <p className="text-gray-400">
        Bootstrap the CAI ledger by importing a CSV of historical allocations.
        <br />
        Format: <code className="bg-gray-800 px-2 py-1 rounded">Symbol,Date(YYYY-MM-DD),Quantity,Price,Allocation Reason</code>
      </p>

      <textarea
        className="w-full h-64 bg-gray-900 border border-gray-700 text-white p-4 font-mono text-sm rounded-lg focus:outline-none focus:border-blue-500"
        placeholder="Symbol,Date,Quantity,Price,Allocation Reason
TCS,2024-01-15,10,3800,D1_ENTRY
TCS,2024-02-10,5,4000,D2_TRANCHE"
        value={csvData}
        onChange={(e) => setCsvData(e.target.value)}
      />

      <button
        onClick={handleImport}
        disabled={loading || !csvData}
        className="flex justify-center items-center py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold rounded-lg transition-colors"
      >
        <Upload className="w-5 h-5 mr-2" />
        {loading ? 'Processing...' : 'Run Initialization'}
      </button>

      {result && (
        <div className={`p-4 rounded-lg border ${result.error ? 'bg-red-500/10 border-red-500/30 text-red-500' : 'bg-green-500/10 border-green-500/30 text-green-500'}`}>
          <h3 className="font-bold mb-2">{result.error ? 'Error' : 'Success'}</h3>
          <pre className="text-sm overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};
