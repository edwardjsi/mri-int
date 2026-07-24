import React, { useEffect, useState } from 'react';
import { getAuthHeaders } from './api';
import { CaiWeeklyChart } from './CaiWeeklyChart';
import { ArrowLeft, Clock, Target } from 'lucide-react';

interface CaiReplayProps {
  reviewId: string;
  onBack: () => void;
}

export const CaiReplay: React.FC<CaiReplayProps> = ({ reviewId, onBack }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReplay = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/cai/portfolio/reviews/${reviewId}/replay`, {
          headers: getAuthHeaders(),
        });
        if (!res.ok) throw new Error('Failed to fetch replay data');
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchReplay();
  }, [reviewId]);

  if (loading) return <div className="p-8 text-center text-gray-400">Loading Replay...</div>;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!data) return null;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <button onClick={onBack} className="flex items-center text-gray-400 hover:text-white transition-colors mb-4">
        <ArrowLeft className="w-4 h-4 mr-2" /> Back
      </button>

      <div className="flex justify-between items-start mb-6 border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center">
            <Clock className="w-8 h-8 mr-3 text-purple-500" />
            Historical Replay: {data.symbol}
          </h1>
          <p className="text-gray-400 mt-2">
            Review Date: {new Date(data.review_date).toLocaleString()}
          </p>
        </div>
        <div className="bg-gray-900 p-4 rounded-xl border border-gray-800 flex space-x-6 text-center">
          <div>
            <p className="text-xs text-gray-500 uppercase">Recommendation</p>
            <p className={`text-lg font-bold ${data.recommendation === 'ADD' ? 'text-green-500' : data.recommendation === 'EXIT' ? 'text-red-500' : 'text-blue-500'}`}>
              {data.recommendation}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Tranche</p>
            <p className="text-lg font-bold text-white">{data.tranche}/10</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Qty</p>
            <p className="text-lg font-bold text-white">{data.quantity}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Avg Price</p>
            <p className="text-lg font-bold text-white">₹{data.average_price.toFixed(2)}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
             <h3 className="text-lg font-bold text-white mb-4">Chart at time of review</h3>
             <CaiWeeklyChart symbol={data.symbol} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-bold text-gray-400 uppercase mb-4 flex items-center">
              <Target className="w-4 h-4 mr-2" /> Recorded Context
            </h3>
            
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-500">Swing Low</p>
                <p className="text-lg font-mono text-white">
                  {data.swing_low ? `₹${data.swing_low.price} (${data.swing_low.date})` : 'Not recorded'}
                </p>
              </div>
              
              <div>
                <p className="text-sm text-gray-500">Structure Break</p>
                <p className="text-lg font-mono text-white">
                  {data.structure_break ? `₹${data.structure_break.price} (${data.structure_break.date})` : 'Not recorded'}
                </p>
              </div>
              
              <div className="pt-4 border-t border-gray-800">
                <p className="text-sm text-gray-500 mb-2">Notes</p>
                <p className="text-sm text-gray-300 whitespace-pre-wrap">
                  {data.notes || 'No notes provided.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
