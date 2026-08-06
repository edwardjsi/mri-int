import React, { useEffect, useState } from 'react';
import { getAuthHeaders } from './api';
import { CaiWeeklyChart } from './CaiWeeklyChart';
import { CaiLedgerTimeline } from './CaiLedgerTimeline';
import { AlertTriangle, TrendingUp, TrendingDown, RefreshCw, XCircle, PlusCircle } from 'lucide-react';

interface CaiPositionReviewProps {
  positionId: string;
  onReviewSaved?: () => void;
  onClose?: () => void;
}

export const CaiPositionReview: React.FC<CaiPositionReviewProps> = ({ positionId, onReviewSaved, onClose }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  
  // Annotation states
  const [notes, setNotes] = useState('');

  useEffect(() => {
    const fetchPosition = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/portfolio-review/position/${positionId}`, {
          headers: getAuthHeaders(),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to evaluate position');
        }
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchPosition();
  }, [positionId]);

  const handleSaveReview = async () => {
    if (!data) return;
    try {
      setSaving(true);
      const res = await fetch('/api/portfolio-review/reviews', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          position_id: positionId,
          recommendation: data.recommendation,
          notes: notes
        })
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to save review');
      }
      
      if (onReviewSaved) onReviewSaved();
      if (onClose) onClose();
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

  return (
    <div className="flex flex-col space-y-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-bold text-white">Position Review: {data?.symbol || 'Loading...'}</h3>
        {onClose && (
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            ✕
          </button>
        )}
      </div>

      {data && (
        <div className="w-full">
          <CaiWeeklyChart symbol={data.symbol} positionData={data} />
        </div>
      )}

      {loading && <div className="text-gray-400">Evaluating position...</div>}
      {error && <div className="text-red-500 p-3 bg-red-500/10 rounded-lg">{error}</div>}
      
      {data && !loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-400">Health Score</p>
                <p className="text-xl font-bold text-white">{data.health_score}/100</p>
              </div>
              <div className="p-3 bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-400">Profit %</p>
                <p className={`text-xl font-bold ${data.profit_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {data.profit_pct > 0 ? '+' : ''}{data.profit_pct}%
                </p>
              </div>
              <div className="p-3 bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-400">Current Tranche</p>
                <p className="text-xl font-bold text-white">{data.tranche}/10</p>
              </div>
            </div>
            
            <div className="pt-2">
              <label className="block text-sm text-gray-400 mb-1">Review Notes</label>
              <textarea 
                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2 text-white h-24 focus:outline-none focus:border-blue-500"
                placeholder="Add swing low, structure break, or story annotations..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex flex-col h-full justify-between space-y-4">
            <div className={`flex-grow p-4 rounded-xl border flex flex-col items-center justify-center text-center ${getRecommendationColor(data.recommendation)}`}>
              <div className="flex items-center text-xl font-bold mb-2">
                {getRecommendationIcon(data.recommendation)}
                {data.recommendation}
              </div>
              <p className="text-sm opacity-90">{data.reason}</p>
            </div>
            
            <button 
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors flex justify-center items-center"
              onClick={handleSaveReview}
              disabled={saving}
            >
              {saving ? 'Saving Review...' : 'Commit Review Decision'}
            </button>
            
            {/* Embed the Timeline below */}
            <CaiLedgerTimeline positionId={positionId} />
          </div>
        </div>
      )}
    </div>
  );
};
