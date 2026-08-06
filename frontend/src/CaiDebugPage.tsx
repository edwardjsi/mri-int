import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiFetch } from './api';
import { ArrowLeft, Server, Activity, FileJson } from 'lucide-react';

interface DebugData {
  symbol: string;
  inputs: {
    current_price: number;
    ema_20_w: number | null;
    ema_50_w: number | null;
    swing_low: number | null;
    breakout_level: number | null;
    atr: number;
  };
  outputs: {
    add_level: number | null;
    alert_level: number | null;
    structure_level: number | null;
    quit_level: number | null;
  };
  decision_state: string;
  algorithm: string;
  calculated_at: string;
}

export const CaiDebugPage: React.FC = () => {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DebugData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;
    const fetchDebug = async () => {
      try {
        const result = await apiFetch(`/cai/portfolio/debug/${symbol}`);
        setData(result);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchDebug();
  }, [symbol]);

  if (loading) {
    return <div className="p-8 text-center text-gray-400 bg-[#0B0F19] h-screen font-mono">Loading debug data...</div>;
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center bg-[#0B0F19] h-screen font-mono">
        <div className="text-red-500 mb-4">{error || 'Failed to load debug data'}</div>
        <button onClick={() => navigate('/caiportfolio')} className="text-indigo-400 hover:underline">
          Return to Portfolio
        </button>
      </div>
    );
  }

  const formatNumber = (val: number | null | undefined) => 
    val != null ? val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : 'N/A';

  const getStateColor = (state: string) => {
    switch (state) {
      case 'ADD': return 'text-green-400 bg-green-900/30';
      case 'HOLD': return 'text-indigo-400 bg-indigo-900/30';
      case 'ALERT': return 'text-amber-400 bg-amber-900/30';
      case 'STRUCTURE': return 'text-orange-400 bg-orange-900/30';
      case 'QUIT': return 'text-red-400 bg-red-900/30';
      default: return 'text-gray-400 bg-gray-900/30';
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-200 p-8 font-mono">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-800 pb-4">
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => navigate('/caiportfolio')}
              className="text-gray-500 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
            <h1 className="text-2xl font-bold text-white flex items-center">
              <Server className="w-6 h-6 mr-3 text-indigo-500" />
              Developer Truth Table <span className="text-gray-500 mx-3">/</span> {data.symbol}
            </h1>
          </div>
          <div className="flex space-x-3">
            <span className="px-3 py-1 bg-gray-800 text-gray-400 rounded-md text-sm border border-gray-700">
              {data.algorithm}
            </span>
            <span className="px-3 py-1 bg-gray-800 text-gray-400 rounded-md text-sm border border-gray-700">
              {data.calculated_at}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8">
          
          {/* Inputs Section */}
          <div className="space-y-4">
            <div className="flex items-center text-gray-400 mb-2">
              <Activity className="w-4 h-4 mr-2" />
              <h2 className="text-sm font-semibold uppercase tracking-wider">Raw Technical Inputs</h2>
            </div>
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden shadow-lg">
              <table className="w-full text-left border-collapse">
                <tbody className="divide-y divide-gray-800/50">
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">Current Price</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.inputs.current_price)}</td>
                  </tr>
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">EMA 20 (Weekly)</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.inputs.ema_20_w)}</td>
                  </tr>
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">EMA 50 (Weekly)</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.inputs.ema_50_w)}</td>
                  </tr>
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">Swing High (10w Bo)</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.inputs.breakout_level)}</td>
                  </tr>
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">Swing Low (4w Low)</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.inputs.swing_low)}</td>
                  </tr>
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">ATR (14w)</td>
                    <td className="py-3 px-4 font-semibold text-gray-500 text-right">{formatNumber(data.inputs.atr)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Outputs Section */}
          <div className="space-y-4">
            <div className="flex items-center text-gray-400 mb-2">
              <FileJson className="w-4 h-4 mr-2" />
              <h2 className="text-sm font-semibold uppercase tracking-wider">Engine Computed Outputs</h2>
            </div>
            
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden shadow-lg mb-6">
              <table className="w-full text-left border-collapse">
                <tbody className="divide-y divide-gray-800/50">
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">Add Level</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.outputs.add_level)}</td>
                  </tr>
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">Alert Level</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.outputs.alert_level)}</td>
                  </tr>
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">Structure Level</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.outputs.structure_level)}</td>
                  </tr>
                  <tr className="hover:bg-gray-800/20 transition-colors">
                    <td className="py-3 px-4 text-gray-400">Quit Level</td>
                    <td className="py-3 px-4 font-semibold text-white text-right">{formatNumber(data.outputs.quit_level)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Decision State */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 shadow-lg flex items-center justify-between">
              <div className="text-gray-400 font-semibold uppercase tracking-wider text-sm">Resolved State</div>
              <div className={`px-4 py-2 rounded-lg font-bold border ${getStateColor(data.decision_state).replace('text-', 'border-').replace('bg-', 'bg-opacity-20 ')} ${getStateColor(data.decision_state)}`}>
                {data.decision_state}
              </div>
            </div>

          </div>
        </div>
        
      </div>
    </div>
  );
};
