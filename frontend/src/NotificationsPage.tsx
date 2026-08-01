
const MOCK_NOTIFICATIONS = [
  { id: 1, type: 'ALERT', symbol: 'INTC', message: 'Price dropped below structural alert level (35.00).', time: '2 hours ago', read: false },
  { id: 2, type: 'ADD', symbol: 'NVDA', message: 'Cleared primary resistance. Target allocation increased.', time: '5 hours ago', read: false },
  { id: 3, type: 'STRUCTURE', symbol: 'AMD', message: 'Nearing overhead supply warning level.', time: '1 day ago', read: true },
  { id: 4, type: 'QUIT', symbol: 'TSLA', message: 'Weekly trend failure confirmed. Immediate exit required.', time: '2 days ago', read: true },
];

const STATE_COLORS = {
  ADD: '#10B981',
  MAINTAIN: '#3B82F6',
  ALERT: '#F59E0B',
  STRUCTURE: '#F97316',
  QUIT: '#EF4444'
} as const;

export default function NotificationsPage() {
  return (
    <div className="p-6 bg-gray-50 min-h-screen font-sans max-w-4xl mx-auto" style={{ fontFamily: 'Inter, sans-serif' }}>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Notifications</h1>
        <button className="text-sm text-blue-600 font-semibold hover:underline">Mark all as read</button>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {MOCK_NOTIFICATIONS.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No new notifications.</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {MOCK_NOTIFICATIONS.map((note) => {
              const stateType = note.type as keyof typeof STATE_COLORS;
              return (
                <div key={note.id} className={`p-4 flex gap-4 ${note.read ? 'bg-white' : 'bg-blue-50'} hover:bg-gray-50 transition-colors`}>
                  <div className="flex-shrink-0 mt-1">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: STATE_COLORS[stateType] }}
                    />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <h3 className="text-sm font-bold text-gray-900">{note.symbol}</h3>
                      <span className="text-xs text-gray-500 font-mono">{note.time}</span>
                    </div>
                    <p className="text-sm text-gray-700 mt-1">{note.message}</p>
                    <div className="mt-2">
                       <span 
                         className="px-2 py-1 rounded text-[10px] uppercase font-bold tracking-wider border"
                         style={{ 
                           backgroundColor: `${STATE_COLORS[stateType]}10`, 
                           color: STATE_COLORS[stateType],
                           borderColor: STATE_COLORS[stateType]
                         }}
                       >
                         {note.type}
                       </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
