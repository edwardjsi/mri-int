import React, { useEffect, useState } from 'react';
import { getAuthHeaders } from './api';
import { CaiWeeklyChart } from './CaiWeeklyChart';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface CaiCandidateReviewProps {
  symbol: string;
  onClose?: () => void;
}

export const CaiCandidateReview: React.FC<CaiCandidateReviewProps> = ({ symbol, onClose }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCandidate = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/portfolio-review/candidate/${symbol}`, {
          headers: getAuthHeaders(),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to evaluate candidate');
        }
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchCandidate();
  }, [symbol]);

  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'BUY FIRST TRANCHE': return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'WATCH': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'REJECT': return 'text-red-500 bg-red-500/10 border-red-500/20';
      default: return 'text-gray-400 bg-gray-800 border-gray-700';
    }
  };

  const getRecommendationIcon = (rec: string) => {
    switch (rec) {
      case 'BUY FIRST TRANCHE': return <CheckCircle className="w-5 h-5 mr-2" />;
      case 'WATCH': return <Clock className="w-5 h-5 mr-2" />;
      case 'REJECT': return <AlertCircle className="w-5 h-5 mr-2" />;
      default: return null;
    }
  };

  return (
    <div className="flex flex-col space-y-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-white">Candidate Review: {symbol}</h3>
        {onClose && (
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            ✕
          </button>
        )}
      </div>

      <div className="w-full">
        <CaiWeeklyChart symbol={symbol} />
      </div>

      {loading && <div className="text-gray-400">Evaluating candidate...</div>}
      
      {error && <div className="text-red-500 p-3 bg-red-500/10 rounded-lg">{error}</div>}
      
      {data && !loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="p-3 bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-400">MRI Score</p>
              <p className="text-xl font-bold text-white">{data.mri_score}/10</p>
            </div>
            <div className="p-3 bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-400">Breakout State</p>
              <p className="text-xl font-bold text-white">{data.breakout_state.replace(/_/g, ' ')}</p>
            </div>
            <div className="p-3 bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-400">RS (90d)</p>
              <p className="text-xl font-bold text-white">{data.rs_90d !== null ? `${data.rs_90d.toFixed(1)}%` : 'N/A'}</p>
            </div>
          </div>
          
          <div className="flex flex-col h-full justify-center space-y-4">
            <div className={`p-4 rounded-xl border flex flex-col items-center justify-center text-center ${getRecommendationColor(data.recommendation)}`}>
              <div className="flex items-center text-lg font-bold mb-2">
                {getRecommendationIcon(data.recommendation)}
                {data.recommendation}
              </div>
              <p className="text-sm opacity-90">{data.reason}</p>
            </div>
            
            {data.recommendation === 'BUY FIRST TRANCHE' && (
              <button 
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                onClick={() => alert(`Adding ${symbol} to Portfolio`)}
              >
                Execute First Tranche
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
