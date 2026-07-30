import React, { useState, useEffect } from 'react';
import { apiFetch } from './api';
import { 
  Briefcase, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  Activity,
  Star,
  Mail,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

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

export const WeeklyReviewDashboard: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState<boolean>(false);
  const [approveStatus, setApproveStatus] = useState<string | null>(null);
  const [emailing, setEmailing] = useState<boolean>(false);
  const [selectedHolding, setSelectedHolding] = useState<any>(null);

  const [sortField, setSortField] = useState<string>('cai_score');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

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

  const handleEmail = async () => {
    try {
      setEmailing(true);
      const result = await apiFetch('/portfolio-review/v1/email-weekly-review', {
        method: 'POST'
      });
      setApproveStatus(result.message || 'Email sent successfully');
    } catch (err: any) {
      setError(err.message || 'Failed to email review');
    } finally {
      setEmailing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-900">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"></div>
          <p className="text-gray-400">Compiling PortfolioOS Analysis...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-8 rounded-lg bg-red-900/30 p-6  border border-red-800/50">
        <div className="flex items-center gap-3 text-red-400">
          <AlertTriangle className="h-6 w-6" />
          <h2 className="text-lg font-semibold">System Error</h2>
        </div>
        <p className="mt-2 text-red-400">{error}</p>
        <div className="flex gap-4 mt-4">
          <button 
            onClick={fetchReviewData}
            className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700 transition"
          >
            Retry
          </button>
          <button 
            onClick={() => setError(null)}
            className="rounded border border-red-700/50 bg-gray-800 px-4 py-2 text-red-400 hover:bg-red-900/30 transition"
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
    review_queue: reviewQueue,
    holdings,
    warnings
  } = data;

  const sortedHoldings = holdings ? [...holdings].sort((a: any, b: any) => {
    let aVal = a[sortField];
    let bVal = b[sortField];
    
    if (sortField === 'value') {
      aVal = a.quantity * a.current_price;
      bVal = b.quantity * b.current_price;
    }
    
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }
    
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  }) : [];

  const totalValue = holdings?.reduce((sum: number, h: any) => sum + (h.quantity * h.current_price), 0) || 0;

  return (
    <div className="min-h-screen bg-gray-900 p-6 font-sans">
      <div className="mx-auto max-w-7xl space-y-6">
        
        {/* Approve Status Banner */}
        {approveStatus && (
          <div className="bg-green-900/30 border border-green-800/50 text-green-300 rounded-xl p-4 flex justify-between items-center ">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span className="font-medium">{approveStatus}</span>
            </div>
            <button onClick={() => setApproveStatus(null)} className="text-green-600 hover:text-green-300 font-bold">&times;</button>
          </div>
        )}
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between bg-gray-800 p-6 rounded-xl  border border-gray-700">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Briefcase className="h-6 w-6 text-indigo-600" />
              Weekly Portfolio Review
            </h1>
            <p className="text-gray-400 mt-1">
              Last Analysis: {new Date(summary.analysis_time).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-3 mt-4 md:mt-0">
            <button 
              onClick={fetchReviewData} 
              disabled={approving || emailing}
              className="flex items-center gap-2 bg-indigo-900/30 text-indigo-300 px-4 py-2 rounded-lg hover:bg-indigo-800/50 transition font-medium disabled:opacity-50"
            >
              <Activity className="h-4 w-4" />
              Re-run
            </button>
            <button 
              onClick={handleEmail} 
              disabled={emailing}
              className="flex items-center gap-2 bg-gray-700 text-white px-4 py-2 rounded-lg hover:bg-gray-600 transition font-medium disabled:opacity-50"
            >
              <Mail className="h-4 w-4" />
              {emailing ? 'Sending...' : 'Email'}
            </button>
            <button 
              onClick={handleApprove} 
              disabled={approving || actionQueue.length === 0}
              className="flex items-center gap-2 bg-green-600 text-white px-5 py-2 rounded-lg hover:bg-green-700 transition font-medium  disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle className="h-4 w-4" />
              {approving ? 'Recording...' : 'Approve Actions'}
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

                <div className="bg-gray-800/10 rounded-lg p-5 backdrop-blur-sm">
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
            <div className="bg-gray-800 rounded-xl  border border-gray-700 overflow-hidden">
              <div className="p-6 border-b border-gray-700 flex justify-between items-center">
                <h2 className="text-lg font-bold text-white">Current Holdings</h2>
                <span className="bg-gray-700 text-gray-400 px-3 py-1 rounded-full text-sm font-medium">
                  {holdings.length} Positions
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-400">
                  <thead className="bg-gray-900 text-white border-b border-gray-700">
                    <tr>
                      <th className="p-4 font-semibold cursor-pointer hover:text-indigo-300" onClick={() => handleSort('ticker')}>Stock</th>
                      <th className="p-4 font-semibold text-right cursor-pointer hover:text-indigo-300" onClick={() => handleSort('quantity')}>Qty</th>
                      <th className="p-4 font-semibold text-right cursor-pointer hover:text-indigo-300" onClick={() => handleSort('value')}>Value (₹)</th>
                      <th className="p-4 font-semibold text-right cursor-pointer hover:text-indigo-300" onClick={() => handleSort('pl_pct')}>P/L %</th>
                      <th className="p-4 font-semibold text-center cursor-pointer hover:text-indigo-300" title="Master Risk Indicator (Stock Quality)" onClick={() => handleSort('mri_score')}>MRI (Quality)</th>
                      <th className="p-4 font-semibold text-center cursor-pointer hover:text-indigo-300" title="Capital Allocation Intelligence (Conviction)" onClick={() => handleSort('cai_score')}>CAI (Conviction)</th>
                      <th className="p-4 font-semibold text-center cursor-pointer hover:text-indigo-300" onClick={() => handleSort('current_action')}>Action</th>
                      <th className="p-4 font-semibold text-center cursor-pointer hover:text-indigo-300" onClick={() => handleSort('review_status')}>Review</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {sortedHoldings.map((h: any, i: number) => (
                      <tr key={i} className="hover:bg-gray-800 transition">
                        <td className="p-4 font-medium text-white">{h.ticker}</td>
                        <td className="p-4 text-right font-medium text-gray-300">{h.quantity}</td>
                        <td className="p-4 text-right font-medium text-gray-300">₹{(h.quantity * h.current_price).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                        <td className={`p-4 text-right font-medium ${h.pl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {h.pl_pct > 0 ? '+' : ''}{h.pl_pct}%
                        </td>
                        <td className="p-4 text-center">
                          <span className={`inline-block px-2 py-1 rounded text-xs font-bold ${h.mri_score >= 80 ? 'bg-green-900/40 text-green-400' : h.mri_score >= 60 ? 'bg-blue-900/40 text-blue-400' : 'bg-gray-700 text-gray-300'}`}>
                            {h.mri_score}
                          </span>
                        </td>
                        <td className="p-4 text-center font-medium">
                          {h.cai_score}
                        </td>
                        <td className="p-4 text-center">
                          <button
                            onClick={() => setSelectedHolding(h)}
                            className={`inline-block px-2 py-1 rounded-md text-xs font-bold hover:opacity-80 transition cursor-pointer ${
                              ['EXIT', 'REDUCE'].includes(h.current_action) ? 'bg-red-900/40 text-red-400' :
                              ['ADD', 'BUY'].includes(h.current_action) ? 'bg-green-900/40 text-green-400' :
                              'bg-gray-700 text-gray-300'
                            }`}
                          >
                            {h.current_action}
                          </button>
                        </td>
                        <td className="p-4 text-center">
                          {h.review_status !== 'NONE' ? (
                            <span className={`inline-block px-2 py-1 rounded-md text-xs font-bold ${
                              h.review_status === 'URGENT_REVIEW' ? 'bg-red-900/40 text-red-400 border border-red-800/50' : 'bg-orange-900/40 text-orange-400 border border-orange-800/50'
                            }`} title={h.review_reason}>
                              {h.review_status === 'URGENT_REVIEW' ? 'URGENT' : 'REVIEW'}
                            </span>
                          ) : (
                            <span className="text-gray-500">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {sortedHoldings.length === 0 && (
                      <tr>
                        <td colSpan={8} className="p-8 text-center text-gray-400">
                          No active holdings found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot className="bg-gray-900 text-white border-t-2 border-gray-700">
                    <tr>
                      <td className="p-4 font-bold">Total</td>
                      <td className="p-4 text-right font-bold text-indigo-400">₹{totalValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                      <td colSpan={4}></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN */}
          <div className="space-y-6">
            
            {/* Section A: Portfolio Overview */}
            <div className="bg-gray-800 rounded-xl  border border-gray-700 p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-indigo-500" />
                Portfolio Overview
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-400">Market Regime</span>
                  <span className="font-semibold text-white">{summary.market_regime}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-400">Health Score</span>
                  <span className="font-bold text-indigo-600">{summary.portfolio_health}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-400">Deployment</span>
                  <span className="font-semibold text-white">{summary.deployment_pct}%</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-400">Cash</span>
                  <span className="font-semibold text-white">₹{summary.cash_available.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-400">Action Items</span>
                  <span className="font-bold text-orange-400">{summary.action_items_count}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-50">
                  <span className="text-gray-400">Review Required</span>
                  <span className="font-bold text-indigo-400">{summary.review_items_count}</span>
                </div>
              </div>
            </div>

            {/* Section F: Portfolio Warnings */}
            {warnings && warnings.length > 0 && (
              <div className="bg-orange-900/30 rounded-xl  border border-orange-800/50 p-6">
                <h2 className="text-lg font-bold text-orange-300 mb-4 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Portfolio Warnings
                </h2>
                <ul className="space-y-3">
                  {warnings.map((w: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-orange-700 text-sm">
                      <span className="mt-1 flex-shrink-0 h-1.5 w-1.5 rounded-full bg-orange-900/300"></span>
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Section C: Action Queue */}
            <div className="bg-gray-800 rounded-xl  border border-gray-700 p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-indigo-500" />
                Action Queue
              </h2>
              <div className="space-y-3">
                {actionQueue.length > 0 ? actionQueue.map((a: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-gray-700 hover:border-indigo-100 hover:bg-indigo-900/30 transition cursor-pointer" onClick={() => setSelectedHolding(a)}>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                            ['EXIT', 'REDUCE'].includes(a.action) ? 'bg-red-900/40 text-red-400' :
                            ['ADD', 'BUY'].includes(a.action) ? 'bg-green-900/40 text-green-400' :
                            'bg-gray-700 text-gray-300'
                        }`}>
                          {a.action}
                        </span>
                        <span className="font-semibold text-white">{a.stock}</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-1 line-clamp-1" title={a.reason}>{a.reason}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-white">{a.confidence}%</div>
                      <div className="text-[10px] text-gray-400 uppercase">Conf.</div>
                    </div>
                  </div>
                )) : (
                  <p className="text-sm text-gray-400 text-center py-4">No pending actions this week.</p>
                )}
              </div>
            </div>

            {/* Section G: Review Queue */}
            {reviewQueue && reviewQueue.length > 0 && (
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
                <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <Activity className="h-5 w-5 text-orange-500" />
                  Review Required
                </h2>
                <div className="space-y-3">
                  {reviewQueue.map((r: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-gray-700 hover:border-orange-800/50 hover:bg-orange-900/10 transition">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                              r.status === 'URGENT_REVIEW' ? 'bg-red-900/40 text-red-400' : 'bg-orange-900/40 text-orange-400'
                          }`}>
                            {r.status === 'URGENT_REVIEW' ? 'URGENT' : 'REVIEW'}
                          </span>
                          <span className="font-semibold text-white">{r.stock}</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">{r.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        </div>
      </div>

      {selectedHolding && (
        <div className="fixed inset-y-0 right-0 w-full md:w-[450px] bg-gray-900 border-l border-gray-700 shadow-2xl transform transition-transform duration-300 ease-in-out z-50 overflow-y-auto flex flex-col">
          <div className="p-6 border-b border-gray-800 flex justify-between items-center sticky top-0 bg-gray-900 z-10">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              {selectedHolding.ticker || selectedHolding.stock} Decision
            </h3>
            <button onClick={() => setSelectedHolding(null)} className="text-gray-400 hover:text-white transition text-2xl leading-none">&times;</button>
          </div>
          
          <div className="p-6 flex-grow">
            {!selectedHolding.explanation_tree ? (
              <div className="bg-red-900/30 p-4 rounded text-red-400 border border-red-800">
                Error: Explanation tree is missing or invalid for this recommendation.
              </div>
            ) : (
              <>
                <Accordion title="Recommendation" defaultOpen={true}>
                  <div className="space-y-2">
                    <div className="flex justify-between border-b border-gray-700 pb-2">
                      <span className="text-gray-400">Action</span>
                      <span className="font-bold text-white">{selectedHolding.current_action || selectedHolding.action}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-700 pb-2">
                      <span className="text-gray-400">Confidence</span>
                      <span className="font-bold text-white">{selectedHolding.confidence}%</span>
                    </div>
                    <div className="pt-1">
                      <span className="text-gray-400 block mb-1">Summary</span>
                      <span>{selectedHolding.primary_reason || selectedHolding.reason}</span>
                    </div>
                  </div>
                </Accordion>
                
                <Accordion title="Why" defaultOpen={true}>
                  <div className="space-y-3">
                    <div>
                      <span className="text-gray-400 block mb-1">Primary Reason</span>
                      <p>{selectedHolding.primary_reason || selectedHolding.reason}</p>
                    </div>
                    {selectedHolding.secondary_reason && (
                      <div>
                        <span className="text-gray-400 block mb-1">Supporting Context</span>
                        <p>{selectedHolding.secondary_reason}</p>
                      </div>
                    )}
                  </div>
                </Accordion>
                
                <Accordion title="Rules">
                  <div className="space-y-3">
                    {selectedHolding.explanation_tree.children && selectedHolding.explanation_tree.children.length > 0 ? (
                      selectedHolding.explanation_tree.children.map((child: any, idx: number) => (
                         <div key={idx} className="bg-gray-900 p-3 rounded border border-gray-700">
                           <div className="font-semibold text-white mb-1">{child.name}</div>
                           <div className="text-xs text-gray-400">Result: <span className="text-gray-200">{child.result}</span></div>
                           {child.details && Object.entries(child.details).map(([k, v]) => (
                             <div key={k} className="text-xs text-gray-400 mt-1">
                               <span className="capitalize">{k.replace(/_/g, ' ')}</span>: {String(v)}
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
                    {selectedHolding.supporting_evidence && selectedHolding.supporting_evidence.length > 0 ? (
                      <ul className="list-disc pl-4 space-y-1">
                        {selectedHolding.supporting_evidence.map((ev: string, i: number) => (
                          <li key={i}>{ev}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-500">No supporting evidence provided.</p>
                    )}
                    
                    {selectedHolding.explanation_tree.details && selectedHolding.explanation_tree.details.calculations && (
                      <div className="mt-4 border-t border-gray-700 pt-3">
                        <h4 className="text-gray-400 mb-2 font-medium">Calculations</h4>
                        {selectedHolding.explanation_tree.details.calculations.map((calc: any, i: number) => (
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
      )}

    </div>
  );
};
