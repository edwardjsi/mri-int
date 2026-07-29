import React, { useState, useEffect } from 'react';
import { apiFetch } from './api';
import { 
  Briefcase, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  Activity,
  Star
} from 'lucide-react';

export const WeeklyReviewDashboard: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState<boolean>(false);
  const [approveStatus, setApproveStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchReviewData();
  }, []);

  const fetchReviewData = async () => {
    try {
      setLoading(true);
      setApproveStatus(null);
      const result = await apiFetch('/portfolio-review/v1/weekly-review');
      setData(result);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch weekly review');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!confirm('Are you sure you want to approve these decisions and record them to the Decision Ledger?')) return;
    try {
      setApproving(true);
      const result = await apiFetch('/portfolio-review/v1/approve-weekly-review', {
        method: 'POST'
      });
      setApproveStatus(`Successfully recorded ${result.recorded_count} actions to the Decision Ledger (Report ID: ${result.report_id || 'N/A'})`);
    } catch (err: any) {
      setError(err.message || 'Failed to approve decisions');
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"></div>
          <p className="text-gray-500">Compiling PortfolioOS Analysis...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-8 rounded-lg bg-red-50 p-6 shadow-sm border border-red-100">
        <div className="flex items-center gap-3 text-red-700">
          <AlertTriangle className="h-6 w-6" />
          <h2 className="text-lg font-semibold">System Error</h2>
        </div>
        <p className="mt-2 text-red-600">{error}</p>
        <div className="flex gap-4 mt-4">
          <button 
            onClick={fetchReviewData}
            className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700 transition"
          >
            Retry
          </button>
          <button 
            onClick={() => setError(null)}
            className="rounded border border-red-200 bg-white px-4 py-2 text-red-600 hover:bg-red-50 transition"
          >
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const {
    portfolio_summary: summary,
    highest_priority_decision: hpDecision,
    action_queue: actionQueue,
    holdings,
    warnings
  } = data;

  return (
    <div className="min-h-screen bg-gray-50 p-6 font-sans">
      <div className="mx-auto max-w-7xl space-y-6">
        
        {/* Approve Status Banner */}
        {approveStatus && (
          <div className="bg-green-50 border border-green-200 text-green-800 rounded-xl p-4 flex justify-between items-center shadow-sm">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span className="font-medium">{approveStatus}</span>
            </div>
            <button onClick={() => setApproveStatus(null)} className="text-green-600 hover:text-green-800 font-bold">&times;</button>
          </div>
        )}
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Briefcase className="h-6 w-6 text-indigo-600" />
              Weekly Portfolio Review
            </h1>
            <p className="text-gray-500 mt-1">
              Last Analysis: {new Date(summary.analysis_time).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-3 mt-4 md:mt-0">
            <button 
              onClick={fetchReviewData} 
              disabled={approving}
              className="flex items-center gap-2 bg-indigo-50 text-indigo-700 px-4 py-2 rounded-lg hover:bg-indigo-100 transition font-medium disabled:opacity-50"
            >
              <Activity className="h-4 w-4" />
              Re-run Analysis
            </button>
            <button 
              onClick={handleApprove} 
              disabled={approving || actionQueue.length === 0}
              className="flex items-center gap-2 bg-green-600 text-white px-5 py-2 rounded-lg hover:bg-green-700 transition font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle className="h-4 w-4" />
              {approving ? 'Recording...' : 'Approve & Record Actions'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* LEFT COLUMN */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Section B: This Week's Decision */}
            {hpDecision && hpDecision.action && (
              <div className="bg-gradient-to-br from-indigo-900 to-indigo-800 rounded-xl shadow-lg border border-indigo-700 p-8 text-white relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-10">
                  <Star className="h-32 w-32" />
                </div>
                <h2 className="text-indigo-200 font-semibold tracking-wider text-sm uppercase flex items-center gap-2 mb-4">
                  <Star className="h-4 w-4 fill-current" />
                  This Week's Decision
                </h2>
                
                <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-8">
                  <div>
                    <h3 className="text-4xl md:text-5xl font-bold mb-2">
                      <span className={
                        hpDecision.action === 'EXIT' ? 'text-red-400' :
                        hpDecision.action === 'REDUCE' ? 'text-orange-400' :
                        hpDecision.action === 'ADD' ? 'text-green-400' :
                        hpDecision.action === 'BUY' ? 'text-emerald-400' : 'text-blue-400'
                      }>{hpDecision.action}</span> {hpDecision.stock}
                    </h3>
                    <p className="text-indigo-200 text-lg">Recommended: {hpDecision.recommended_amount}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-4xl font-bold">{hpDecision.confidence}%</div>
                    <div className="text-indigo-200 text-sm uppercase tracking-wider">Confidence</div>
                  </div>
                </div>

                <div className="bg-white/10 rounded-lg p-5 backdrop-blur-sm">
                  <h4 className="font-semibold text-indigo-100 mb-2 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" /> Reason
                  </h4>
                  <p className="text-white text-lg">{hpDecision.reason}</p>
                  <div className="flex gap-4 mt-4 pt-4 border-t border-white/10">
                    <div>
                      <span className="text-indigo-200 text-sm block">MRI Score</span>
                      <span className="font-bold text-xl">{hpDecision.mri_score}</span>
                    </div>
                    <div>
                      <span className="text-indigo-200 text-sm block">CAI Score</span>
                      <span className="font-bold text-xl">{hpDecision.cai_score}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Section D: Holdings Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                <h2 className="text-lg font-bold text-gray-900">Current Holdings</h2>
                <span className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full text-sm font-medium">
                  {holdings.length} Positions
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600">
                  <thead className="bg-gray-50 text-gray-900 border-b border-gray-100">
                    <tr>
                      <th className="p-4 font-semibold">Stock</th>
                      <th className="p-4 font-semibold text-right">P/L %</th>
                      <th className="p-4 font-semibold text-center">MRI</th>
                      <th className="p-4 font-semibold text-center">CAI</th>
                      <th className="p-4 font-semibold text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {holdings.map((h: any, i: number) => (
                      <tr key={i} className="hover:bg-gray-50 transition">
                        <td className="p-4 font-medium text-gray-900">{h.ticker}</td>
                        <td className={`p-4 text-right font-medium ${h.pl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {h.pl_pct > 0 ? '+' : ''}{h.pl_pct}%
                        </td>
                        <td className="p-4 text-center">
                          <span className={`inline-block px-2 py-1 rounded text-xs font-bold ${h.mri_score >= 80 ? 'bg-green-100 text-green-700' : h.mri_score >= 60 ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>
                            {h.mri_score}
                          </span>
                        </td>
                        <td className="p-4 text-center font-medium">{h.cai_score}</td>
                        <td className="p-4 text-center">
                          <span className={`inline-block px-2 py-1 rounded-md text-xs font-bold ${
                            ['EXIT', 'REDUCE'].includes(h.current_action) ? 'bg-red-100 text-red-700' :
                            ['ADD', 'BUY'].includes(h.current_action) ? 'bg-green-100 text-green-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {h.current_action}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {holdings.length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-gray-500">
                          No active holdings found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN */}
          <div className="space-y-6">
            
            {/* Section A: Portfolio Overview */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-indigo-500" />
                Portfolio Overview
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-500">Market Regime</span>
                  <span className="font-semibold text-gray-900">{summary.market_regime}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-500">Health Score</span>
                  <span className="font-bold text-indigo-600">{summary.portfolio_health}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-500">Deployment</span>
                  <span className="font-semibold text-gray-900">{summary.deployment_pct}%</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-500">Cash</span>
                  <span className="font-semibold text-gray-900">₹{summary.cash_available.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-500">Action Items</span>
                  <span className="font-bold text-orange-600">{summary.action_items_count}</span>
                </div>
              </div>
            </div>

            {/* Section F: Portfolio Warnings */}
            {warnings && warnings.length > 0 && (
              <div className="bg-orange-50 rounded-xl shadow-sm border border-orange-100 p-6">
                <h2 className="text-lg font-bold text-orange-800 mb-4 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Portfolio Warnings
                </h2>
                <ul className="space-y-3">
                  {warnings.map((w: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-orange-700 text-sm">
                      <span className="mt-1 flex-shrink-0 h-1.5 w-1.5 rounded-full bg-orange-500"></span>
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Section C: Action Queue */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-indigo-500" />
                Action Queue
              </h2>
              <div className="space-y-3">
                {actionQueue.length > 0 ? actionQueue.map((a: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-indigo-100 hover:bg-indigo-50/30 transition">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                            ['EXIT', 'REDUCE'].includes(a.action) ? 'bg-red-100 text-red-700' :
                            ['ADD', 'BUY'].includes(a.action) ? 'bg-green-100 text-green-700' :
                            'bg-gray-100 text-gray-700'
                        }`}>
                          {a.action}
                        </span>
                        <span className="font-semibold text-gray-900">{a.stock}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1 line-clamp-1" title={a.reason}>{a.reason}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-gray-900">{a.confidence}%</div>
                      <div className="text-[10px] text-gray-500 uppercase">Conf.</div>
                    </div>
                  </div>
                )) : (
                  <p className="text-sm text-gray-500 text-center py-4">No pending actions this week.</p>
                )}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};
