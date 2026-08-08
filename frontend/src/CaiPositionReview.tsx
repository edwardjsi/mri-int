import React, { useEffect, useMemo, useState } from 'react';
import { getAuthHeaders } from './api';
import { CaiWeeklyChart } from './CaiWeeklyChart';
import { CaiLedgerTimeline } from './CaiLedgerTimeline';
import { AlertTriangle, TrendingUp, TrendingDown, RefreshCw, XCircle, PlusCircle } from 'lucide-react';

interface CaiPositionReviewProps {
  positionId: string;
  onReviewSaved?: () => void;
  onClose?: () => void;
}

type EditForm = {
  pullback_lower_bound: string;
  pullback_upper_bound: string;
  breakout_confirmation_price: string;
  next_add_price: string;
  structural_break_price: string;
};

const emptyEditForm: EditForm = {
  pullback_lower_bound: '',
  pullback_upper_bound: '',
  breakout_confirmation_price: '',
  next_add_price: '',
  structural_break_price: ''
};

export const CaiPositionReview: React.FC<CaiPositionReviewProps> = ({ positionId, onReviewSaved, onClose }) => {
  const [data, setData] = useState<any>(null);
  const [caiConfig, setCaiConfig] = useState<any>(null);
  const [caiConfigError, setCaiConfigError] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [editForm, setEditForm] = useState<EditForm>(emptyEditForm);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState('');
  const [syncing, setSyncing] = useState(false);

  const duplicateThreshold = useMemo(() => {
    if (!caiConfig) return false;
    const breakout = Number(caiConfig.breakout_confirmation_price);
    const nextAdd = Number(caiConfig.next_add_price);
    return Number.isFinite(breakout) && Number.isFinite(nextAdd) && breakout === nextAdd;
  }, [caiConfig]);

  useEffect(() => {
    const fetchPosition = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`/api/portfolio-review/position/${positionId}`, {
          headers: getAuthHeaders(),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to evaluate position');
        }
        setData(await res.json());
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchPosition();
  }, [positionId]);

  const loadCaiConfig = async (symbol: string) => {
    try {
      const res = await fetch(`/api/cai/alerts/${symbol}`, { headers: getAuthHeaders() });
      if (!res.ok) {
        setCaiConfigError(true);
        return;
      }
      const json = await res.json();
      const activeConfig = json.draft || json.approved || null;
      setCaiConfig(activeConfig);
      setCaiConfigError(false);
      if (activeConfig) {
        setEditForm({
          pullback_lower_bound: activeConfig.pullback_lower_bound ?? '',
          pullback_upper_bound: activeConfig.pullback_upper_bound ?? '',
          breakout_confirmation_price: activeConfig.breakout_confirmation_price ?? '',
          next_add_price: activeConfig.next_add_price ?? '',
          structural_break_price: activeConfig.structural_break_price ?? ''
        });
      } else {
        setEditForm(emptyEditForm);
      }
    } catch (err) {
      console.error('Failed to fetch CAI config', err);
      setCaiConfigError(true);
    }
  };

  useEffect(() => {
    if (data?.symbol) void loadCaiConfig(data.symbol);
  }, [data?.symbol]);

  const handleSaveReview = async () => {
    if (!data) return;
    try {
      setSaving(true);
      const res = await fetch('/api/portfolio-review/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ position_id: positionId, recommendation: data.recommendation, notes })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to save review');
      }
      onReviewSaved?.();
      onClose?.();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'ADD': return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'WAIT': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'HOLD': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
      case 'REDUCE': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
      case 'EXIT': return 'text-red-500 bg-red-500/10 border-red-500/20';
      case 'ROTATE': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
      default: return 'text-gray-400 bg-gray-800 border-gray-700';
    }
  };

  const getRecommendationIcon = (rec: string) => {
    switch (rec) {
      case 'ADD': return <PlusCircle className="w-5 h-5 mr-2" />;
      case 'WAIT': return <AlertTriangle className="w-5 h-5 mr-2" />;
      case 'HOLD': return <TrendingUp className="w-5 h-5 mr-2" />;
      case 'REDUCE': return <TrendingDown className="w-5 h-5 mr-2" />;
      case 'EXIT': return <XCircle className="w-5 h-5 mr-2" />;
      case 'ROTATE': return <RefreshCw className="w-5 h-5 mr-2" />;
      default: return null;
    }
  };

  const saveDraft = async () => {
    if (!data?.symbol) return;
    const payload = {
      pullback_lower_bound: editForm.pullback_lower_bound ? parseFloat(editForm.pullback_lower_bound) : null,
      pullback_upper_bound: editForm.pullback_upper_bound ? parseFloat(editForm.pullback_upper_bound) : null,
      breakout_confirmation_price: editForm.breakout_confirmation_price ? parseFloat(editForm.breakout_confirmation_price) : null,
      next_add_price: editForm.next_add_price ? parseFloat(editForm.next_add_price) : null,
      structural_break_price: editForm.structural_break_price ? parseFloat(editForm.structural_break_price) : null
    };
    const res = await fetch(`/api/cai/alerts/${data.symbol}/draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to save draft');
    }
    setShowEditModal(false);
    await loadCaiConfig(data.symbol);
  };

  const openPreview = async () => {
    if (!data?.symbol || !caiConfig) return;
    const res = await fetch(`/api/cai/alerts/${data.symbol}/preview`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || 'Failed to load sync preview');
      return;
    }
    setPreviewData(await res.json());
    setShowPreviewModal(true);
  };

  const sendAlertsToZerodha = async () => {
    if (!data?.symbol || !caiConfig || caiConfig.status !== 'DRAFT' || duplicateThreshold) return;
    const confirmed = window.confirm(
      `Send the 4 CAI alerts for ${data.symbol} to Zerodha?\n\n` +
      'This creates/replaces only CAI-owned alerts. No orders, GTTs, or ATOs will be placed.'
    );
    if (!confirmed) return;

    try {
      setSyncing(true);
      const res = await fetch(`/api/cai/alerts/${data.symbol}/approve-sync`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Sync failed');
      }
      alert('4 CAI alerts synchronized successfully.');
      await loadCaiConfig(data.symbol);
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex flex-col space-y-6 w-full pb-8">
      <div className="flex justify-between items-center border-b border-gray-800 pb-4">
        <div>
          <h3 className="text-xl font-bold text-white">Position Review: {data?.symbol || 'Loading...'}</h3>
          <p className="text-xs text-gray-500 mt-1">Saturday CAI review → preview → send alerts to Zerodha</p>
        </div>
        {onClose && <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>}
      </div>

      {data && <div className="w-full"><CaiWeeklyChart symbol={data.symbol} positionData={data} caiConfig={caiConfig} /></div>}

      {data && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 mt-4">
          <div className="flex justify-between items-center mb-4 pb-2 border-b border-gray-700">
            <h4 className="text-lg font-bold text-white">CAI Alert Orchestration</h4>
            <div className={`px-3 py-1 rounded text-xs font-bold ${
              caiConfigError ? 'bg-red-900/50 text-red-200' :
              !caiConfig ? 'bg-gray-700 text-gray-300' :
              caiConfig.status === 'APPROVED' ? 'bg-green-500/20 text-green-400' :
              'bg-orange-500/20 text-orange-400'
            }`}>
              Status: {caiConfigError ? 'CAI CONFIG LOAD ERROR' : !caiConfig ? 'UNCONFIGURED' : caiConfig.status === 'DRAFT' ? 'DRAFT' : caiConfig.status}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-900 p-3 rounded border border-gray-800">
              <div className="text-gray-400 text-xs mb-1">🟢 Healthy Pullback</div>
              <div className="text-white font-mono">{caiConfig?.pullback_lower_bound != null ? `₹${caiConfig.pullback_lower_bound} - ₹${caiConfig.pullback_upper_bound}` : '—'}</div>
            </div>
            <div className="bg-gray-900 p-3 rounded border border-gray-800">
              <div className="text-gray-400 text-xs mb-1">🚀 Breakout Confirmation</div>
              <div className="text-white font-mono">{caiConfig?.breakout_confirmation_price != null ? `₹${caiConfig.breakout_confirmation_price}` : '—'}</div>
            </div>
            <div className="bg-gray-900 p-3 rounded border border-gray-800">
              <div className="text-gray-400 text-xs mb-1">➕ Next ADD</div>
              <div className="text-white font-mono">{caiConfig?.next_add_price != null ? `₹${caiConfig.next_add_price}` : '—'}</div>
            </div>
            <div className="bg-gray-900 p-3 rounded border border-red-900/50">
              <div className="text-red-400 text-xs mb-1">🔴 Structure Break</div>
              <div className="text-white font-mono">{caiConfig?.structural_break_price != null ? `₹${caiConfig.structural_break_price}` : '—'}</div>
            </div>
          </div>

          {duplicateThreshold && (
            <div className="mb-4 p-4 bg-yellow-900/40 border border-yellow-500/50 rounded text-yellow-400 text-sm">
              <div className="flex items-center font-bold text-base mb-1">
                <AlertTriangle className="w-5 h-5 mr-2 text-yellow-500" />
                BREAKOUT = NEXT ADD — REVIEW REQUIRED
              </div>
              <div className="ml-7 text-yellow-200">
                Breakout confirms strength; Next ADD authorizes the next tranche. These must be deliberately separated before alerts can be sent.
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-3 mt-4 items-center">
            {caiConfig?.status === 'DRAFT' && (
              <button
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm transition-colors"
                onClick={() => setShowEditModal(true)}
              >
                EDIT DRAFT
              </button>
            )}
            <button
              className="px-4 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-600/30 rounded text-sm transition-colors"
              onClick={openPreview}
              disabled={!caiConfig}
            >
              VIEW SYNC PREVIEW
            </button>
            {caiConfig?.status === 'DRAFT' && (
              <button
                className={`px-5 py-2 rounded text-sm font-bold transition-colors ml-auto ${
                  duplicateThreshold || syncing
                    ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
                    : 'bg-green-600 hover:bg-green-500 text-white'
                }`}
                disabled={duplicateThreshold || syncing}
                onClick={sendAlertsToZerodha}
                title={duplicateThreshold ? 'Resolve BREAKOUT = NEXT ADD before sending alerts' : 'Create/replace the four CAI-owned Zerodha alerts'}
              >
                {duplicateThreshold ? 'SEND ALERTS TO ZERODHA — BLOCKED' : syncing ? 'SENDING ALERTS…' : 'SEND ALERTS TO ZERODHA'}
              </button>
            )}
          </div>

          {caiConfig?.status === 'APPROVED' && (
            <div className="mt-4 text-sm text-green-400 bg-green-900/20 border border-green-900/40 rounded p-3">
              ✓ CAI alerts are already APPROVED and synchronized. No send action is available until a new DRAFT is created.
            </div>
          )}
        </div>
      )}

      {loading && <div className="text-gray-400">Evaluating position...</div>}
      {error && <div className="text-red-500 p-3 bg-red-500/10 rounded-lg">{error}</div>}

      {data && !loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-gray-800 rounded-lg"><p className="text-sm text-gray-400">Health Score</p><p className="text-xl font-bold text-white">{data.health_score}/100</p></div>
              <div className="p-3 bg-gray-800 rounded-lg"><p className="text-sm text-gray-400">Profit %</p><p className={`text-xl font-bold ${data.profit_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>{data.profit_pct > 0 ? '+' : ''}{data.profit_pct}%</p></div>
              <div className="p-3 bg-gray-800 rounded-lg"><p className="text-sm text-gray-400">Current Tranche</p><p className="text-xl font-bold text-white">{data.tranche}/10</p></div>
            </div>
            <div className="pt-2">
              <label className="block text-sm text-gray-400 mb-1">Review Notes</label>
              <textarea className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white h-24 focus:outline-none focus:border-blue-500" placeholder="Add swing low, structure break, or story annotations..." value={notes} onChange={e => setNotes(e.target.value)} />
            </div>
          </div>
          <div className="flex flex-col h-full justify-between space-y-4">
            <div className={`flex-grow p-4 rounded-xl border flex flex-col items-center justify-center text-center ${getRecommendationColor(data.recommendation)}`}>
              <div className="flex items-center text-xl font-bold mb-2">{getRecommendationIcon(data.recommendation)}{data.recommendation}</div>
              <p className="text-sm opacity-90">{data.reason}</p>
            </div>
            <button className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors flex justify-center items-center" onClick={handleSaveReview} disabled={saving}>{saving ? 'Saving Review...' : 'Commit Review Decision'}</button>
            <CaiLedgerTimeline positionId={positionId} />
          </div>
        </div>
      )}

      {showEditModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-[500px] max-w-full">
            <h3 className="text-xl font-bold text-white mb-4">Edit CAI Draft: {data?.symbol}</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-sm text-gray-400 mb-1">Pullback Lower</label><input type="number" className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" value={editForm.pullback_lower_bound} onChange={e => setEditForm({...editForm, pullback_lower_bound: e.target.value})} /></div>
                <div><label className="block text-sm text-gray-400 mb-1">Pullback Upper</label><input type="number" className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" value={editForm.pullback_upper_bound} onChange={e => setEditForm({...editForm, pullback_upper_bound: e.target.value})} /></div>
              </div>
              <div><label className="block text-sm text-gray-400 mb-1">Breakout Confirmation</label><input type="number" className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" value={editForm.breakout_confirmation_price} onChange={e => setEditForm({...editForm, breakout_confirmation_price: e.target.value})} /></div>
              <div><label className="block text-sm text-gray-400 mb-1">Next ADD</label><input type="number" className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" value={editForm.next_add_price} onChange={e => setEditForm({...editForm, next_add_price: e.target.value})} /></div>
              <div><label className="block text-sm text-red-400 mb-1">Structure Break</label><input type="number" className="w-full bg-gray-800 border border-red-900 rounded p-2 text-white" value={editForm.structural_break_price} onChange={e => setEditForm({...editForm, structural_break_price: e.target.value})} /></div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button className="px-4 py-2 text-gray-400 hover:text-white" onClick={() => setShowEditModal(false)}>Cancel</button>
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded" onClick={async () => { try { await saveDraft(); } catch (err: any) { alert(err.message); } }}>Save Draft</button>
            </div>
          </div>
        </div>
      )}

      {showPreviewModal && previewData && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-[600px] max-w-full">
            <h3 className="text-xl font-bold text-white mb-4">Sync Preview: {data?.symbol}</h3>
            <p className="text-gray-400 text-sm mb-2">Only CAI-owned Zerodha alerts will be created, updated, or replaced.</p>
            <div className="bg-gray-800 rounded p-3 text-sm font-mono text-gray-300">
              {previewData.changes?.length === 0 && <span className="text-gray-500">No changes detected.</span>}
              {previewData.changes?.map((c: any, i: number) => (
                <div key={i} className="mb-2 border-b border-gray-700 pb-2 last:border-0">
                  <span className="text-white font-bold">{c.role}</span>
                  <div className="ml-4 mt-1">
                    {c.action === 'CREATE' && <span className="text-green-400">CREATE: ₹{c.new}</span>}
                    {c.action === 'UPDATE' && <span className="text-blue-400">UPDATE: ₹{c.old} ➔ ₹{c.new}</span>}
                    {c.action === 'DELETE' && <span className="text-red-400">DELETE (was ₹{c.old})</span>}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">Unchanged: {previewData.unchanged_count ?? 0} | Unrelated: {previewData.unrelated_count ?? 0}</p>
            <div className="flex justify-end mt-4"><button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded" onClick={() => setShowPreviewModal(false)}>Close</button></div>
          </div>
        </div>
      )}
    </div>
  );
};
