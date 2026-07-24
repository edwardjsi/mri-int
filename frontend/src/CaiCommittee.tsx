import React, { useState } from 'react';
import { getAuthHeaders } from './api';
import { FileText, CheckCircle, Clock } from 'lucide-react';

export const CaiCommittee: React.FC = () => {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/portfolio-review/committee/generate', {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to generate report');
      setReport(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!report?.report_id) return;
    try {
      setApproving(true);
      const res = await fetch(`/api/portfolio-review/committee/approve/${report.report_id}`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to approve report');
      alert(data.message);
      setReport(null); // Clear the report after approval
    } catch (err: any) {
      alert(err.message);
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="p-6 bg-gray-900 border border-gray-800 rounded-xl space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center">
            <FileText className="w-6 h-6 mr-2 text-blue-500" />
            Investment Committee
          </h2>
          <p className="text-gray-400 mt-1">Review and approve this week's position changes.</p>
        </div>
        <button 
          onClick={handleGenerate}
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
          {loading ? 'Generating...' : 'Generate Weekly Report'}
        </button>
      </div>

      {error && <div className="p-4 bg-red-500/10 text-red-500 border border-red-500/20 rounded-lg">{error}</div>}

      {report && (
        <div className="space-y-6 border border-gray-700 rounded-xl p-6 bg-gray-800/50">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-white flex items-center">
              <Clock className="w-5 h-5 mr-2 text-yellow-500" />
              Pending Report ID: {report.report_id.slice(0,8)}...
            </h3>
            <button
              onClick={handleApprove}
              disabled={approving}
              className="bg-green-600 hover:bg-green-500 text-white px-6 py-2 rounded-lg font-medium transition-colors flex items-center"
            >
              <CheckCircle className="w-5 h-5 mr-2" />
              {approving ? 'Approving...' : 'Approve & Push to Ledger'}
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {report.decisions.map((d: any, idx: number) => (
              <div key={idx} className="p-4 bg-gray-800 border border-gray-700 rounded-lg flex justify-between items-center">
                <span className="font-bold text-lg text-white">{d.symbol}</span>
                <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                  d.recommendation === 'ADD' ? 'bg-green-500/20 text-green-500' :
                  d.recommendation === 'EXIT' ? 'bg-red-500/20 text-red-500' :
                  d.recommendation === 'REDUCE' ? 'bg-orange-500/20 text-orange-500' :
                  'bg-gray-500/20 text-gray-400'
                }`}>
                  {d.recommendation}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
