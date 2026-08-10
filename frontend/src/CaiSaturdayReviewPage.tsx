import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAuthHeaders } from './api';
import { AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface PositionData {
  id: string;
  symbol: string;
  tranche: number;
  config_status: string;
  validation_status: string | null;
  validation_reasons: string[] | null;
  pullback_lower: number | null;
  pullback_upper: number | null;
  breakout: number | null;
  next_add: number | null;
  structure_break: number | null;
  zerodha_sync_status: string | null;
}

interface SaturdayReviewData {
  review_date: string;
  total_positions: number;
  reviewed: number;
  approved_and_synced: number;
  remaining: number;
  positions: PositionData[];
}

export const CaiSaturdayReviewPage: React.FC = () => {
  const [data, setData] = useState<SaturdayReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchReviewData = async () => {
      try {
        setLoading(true);
        const res = await fetch('/api/cai/saturday-review', {
          headers: getAuthHeaders(),
        });
        if (!res.ok) {
          throw new Error('Failed to fetch Saturday review data');
        }
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchReviewData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-[#0f172a]">
        <div className="text-gray-400">Loading Saturday Review...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center bg-[#0f172a]">
        <div className="text-red-500 bg-red-500/10 p-4 rounded-lg">Error: {error}</div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex flex-col h-full bg-[#0f172a] text-gray-200 p-6 overflow-y-auto">
      <div className="max-w-7xl mx-auto w-full">
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-white mb-2">CAI SATURDAY REVIEW</h1>
          
          <div className="flex items-center gap-6 mt-4">
            <div className="bg-gray-800/80 px-4 py-3 rounded-lg border border-gray-700">
              <div className="text-2xl font-bold text-white">{data.total_positions}</div>
              <div className="text-xs text-gray-400 uppercase font-semibold">Active Positions</div>
            </div>
            
            <div className="bg-gray-800/80 px-4 py-3 rounded-lg border border-gray-700">
              <div className="text-2xl font-bold text-gray-300">{data.reviewed}</div>
              <div className="text-xs text-gray-400 uppercase font-semibold">Reviewed</div>
            </div>

            <div className="bg-green-900/20 px-4 py-3 rounded-lg border border-green-700/30">
              <div className="text-2xl font-bold text-green-400">{data.approved_and_synced}</div>
              <div className="text-xs text-green-500/80 uppercase font-semibold">Approved & Synced</div>
            </div>

            <div className="bg-blue-900/20 px-4 py-3 rounded-lg border border-blue-700/30">
              <div className="text-2xl font-bold text-blue-400">{data.remaining}</div>
              <div className="text-xs text-blue-500/80 uppercase font-semibold">Remaining</div>
            </div>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-gray-800 text-gray-400 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-4">Stock</th>
                <th className="px-6 py-4">Tranche</th>
                <th className="px-6 py-4">Pullback</th>
                <th className="px-6 py-4">Breakout</th>
                <th className="px-6 py-4">Next ADD</th>
                <th className="px-6 py-4">Structure</th>
                <th className="px-6 py-4">Validation</th>
                <th className="px-6 py-4">State</th>
                <th className="px-6 py-4">Zerodha</th>
                <th className="px-6 py-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {data.positions.map((pos) => {
                const isUnconfigured = pos.config_status === 'UNCONFIGURED';
                const isSynced = pos.zerodha_sync_status === 'SYNCED';
                
                return (
                  <tr key={pos.symbol} className="hover:bg-gray-800/50 transition-colors">
                    <td className="px-6 py-4 font-bold text-white">{pos.symbol}</td>
                    <td className="px-6 py-4 text-gray-400">T{pos.tranche}</td>
                    
                    {isUnconfigured ? (
                      <td colSpan={4} className="px-6 py-4 text-gray-500 italic text-center">
                        MRI data insufficient
                      </td>
                    ) : (
                      <>
                        <td className="px-6 py-4 text-green-400 font-mono">
                          {pos.pullback_lower ? `${pos.pullback_lower}–${pos.pullback_upper}` : (pos.pullback_upper || '—')}
                        </td>
                        <td className="px-6 py-4 text-blue-400 font-mono">{pos.breakout || '—'}</td>
                        <td className="px-6 py-4 text-purple-400 font-mono">{pos.next_add || '—'}</td>
                        <td className="px-6 py-4 text-red-400 font-mono">{pos.structure_break || '—'}</td>
                      </>
                    )}

                    <td className="px-6 py-4">
                      {pos.validation_status === 'READY' ? (
                        <span className="flex items-center text-green-400 font-bold text-xs bg-green-500/10 px-2 py-1 rounded w-fit">
                          <CheckCircle className="w-3 h-3 mr-1" /> READY
                        </span>
                      ) : pos.validation_status === 'INVALID' ? (
                        <div className="flex flex-col gap-1">
                          <span className="flex items-center text-red-500 font-bold text-xs bg-red-500/10 px-2 py-1 rounded w-fit">
                            <AlertTriangle className="w-3 h-3 mr-1" /> INVALID
                          </span>
                          {(pos.validation_reasons || []).map((reason: string) => (
                            <span key={reason} className="text-red-400/80 text-[10px] uppercase font-mono">{reason}</span>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-col gap-1">
                          <span className="flex items-center text-yellow-500 font-bold text-xs bg-yellow-500/10 px-2 py-1 rounded w-fit">
                            <AlertTriangle className="w-3 h-3 mr-1" /> REVIEW REQUIRED
                          </span>
                          {(pos.validation_reasons || []).map((reason: string) => (
                            <span key={reason} className="text-yellow-500/80 text-[10px] uppercase font-mono">{reason}</span>
                          ))}
                        </div>
                      )}
                    </td>

                    <td className="px-6 py-4">
                      {pos.config_status === 'APPROVED' ? (
                        <span className="text-green-500 font-bold">{pos.config_status}</span>
                      ) : pos.config_status === 'DRAFT' ? (
                        <span className="text-orange-400 font-bold">{pos.config_status}</span>
                      ) : (
                        <span className="text-gray-500">{pos.config_status}</span>
                      )}
                    </td>

                    <td className="px-6 py-4">
                      {isSynced ? (
                        <span className="flex items-center text-green-400 font-semibold">
                          <CheckCircle className="w-4 h-4 mr-1" /> ✓ SYNCED
                        </span>
                      ) : pos.config_status === 'APPROVED' ? (
                        <span className="flex items-center text-yellow-500 font-semibold">
                          <Clock className="w-4 h-4 mr-1" /> PENDING
                        </span>
                      ) : (
                        <span className="text-gray-600">—</span>
                      )}
                    </td>

                    <td className="px-6 py-4 text-center">
                      <button
                        onClick={() => navigate(`/caiposition/${pos.id}?from=saturday`)}
                        className="bg-gray-700 hover:bg-blue-600 text-white font-bold py-1.5 px-4 rounded text-xs transition-colors shadow-sm"
                      >
                        REVIEW
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
