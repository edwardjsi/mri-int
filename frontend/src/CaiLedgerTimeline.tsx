import React, { useEffect, useState } from 'react';
import { apiFetch } from './api';
import { CheckCircle2, Clock } from 'lucide-react';

interface LedgerEvent {
  id: string;
  event_type: string;
  allocation_reason: string;
  execution_date: string;
  price: number;
  quantity: number;
  capital_allocated: number;
  decision_state: string;
  decision_ladder_version: string;
}

export const CaiLedgerTimeline: React.FC<{ positionId: string }> = ({ positionId }) => {
  const [events, setEvents] = useState<LedgerEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<LedgerEvent | null>(null);

  useEffect(() => {
    const fetchLedger = async () => {
      try {
        const data = await apiFetch(`/cai/portfolio/positions/${positionId}/ledger`);
        setEvents(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchLedger();
  }, [positionId]);

  if (loading) return <div className="text-gray-400">Loading ledger...</div>;
  if (error) return <div className="text-red-500">Error: {error}</div>;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mt-4 text-sm text-gray-200">
      <h3 className="text-lg font-bold text-white mb-4">Capital Allocation Ledger</h3>
      
      <div className="relative border-l border-gray-700 ml-3 space-y-6">
        {events.map((event) => (
          <div key={event.id} className="relative pl-6">
            <span className="absolute -left-[11px] top-1 bg-gray-900">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            </span>
            <div 
              className="bg-gray-800/50 p-3 rounded-lg border border-gray-700 hover:border-blue-500 cursor-pointer transition-colors"
              onClick={() => setSelectedEvent(event)}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="font-bold text-blue-400">{event.allocation_reason}</span>
                <span className="text-gray-400 text-xs">{event.execution_date.split(' ')[0]}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>{event.quantity} shares @ ₹{event.price}</span>
                <span className="text-gray-500 text-xs">Vol: ₹{event.capital_allocated}</span>
              </div>
            </div>
          </div>
        ))}
        
        {/* Next Pending Tranche mock */}
        <div className="relative pl-6 opacity-60">
          <span className="absolute -left-[11px] top-1 bg-gray-900">
            <Clock className="w-5 h-5 text-gray-500" />
          </span>
          <div className="bg-gray-800/20 p-3 rounded-lg border border-gray-700 border-dashed">
            <div className="flex justify-between items-center">
              <span className="font-bold text-gray-500">D{events.length + 1}_TRANCHE (Pending)</span>
            </div>
            <p className="text-gray-500 text-xs mt-1">Awaiting next engine ADD signal...</p>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-md w-full p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-gray-800 pb-2">
              <h4 className="font-bold text-lg text-white">Immutable Event Log</h4>
              <button onClick={() => setSelectedEvent(null)} className="text-gray-500 hover:text-white">✕</button>
            </div>
            <table className="w-full text-left">
              <tbody className="divide-y divide-gray-800">
                <tr><td className="py-2 text-gray-400">Event ID</td><td className="py-2 text-xs truncate">{selectedEvent.id}</td></tr>
                <tr><td className="py-2 text-gray-400">Event Type</td><td className="py-2 font-bold text-green-400">{selectedEvent.event_type}</td></tr>
                <tr><td className="py-2 text-gray-400">Reason</td><td className="py-2">{selectedEvent.allocation_reason}</td></tr>
                <tr><td className="py-2 text-gray-400">Date</td><td className="py-2">{selectedEvent.execution_date}</td></tr>
                <tr><td className="py-2 text-gray-400">Price</td><td className="py-2">₹{selectedEvent.price}</td></tr>
                <tr><td className="py-2 text-gray-400">Quantity</td><td className="py-2">{selectedEvent.quantity}</td></tr>
                <tr><td className="py-2 text-gray-400">Decision State</td><td className="py-2">{selectedEvent.decision_state || 'N/A'}</td></tr>
                <tr><td className="py-2 text-gray-400">Version</td><td className="py-2">{selectedEvent.decision_ladder_version || 'N/A'}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
