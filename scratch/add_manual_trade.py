import re

with open("frontend/src/CaiPortfolioPage.tsx", "r") as f:
    content = f.read()

# Add state variables
state_vars = """  const [activeTab, setActiveTab] = useState<'portfolio' | 'committee' | 'ledger'>('portfolio');
  const [showManualTrade, setShowManualTrade] = useState(false);
  const [tradeType, setTradeType] = useState<'NEW' | 'TRANCHE'>('NEW');
  const [tradeSymbol, setTradeSymbol] = useState('');
  const [tradeQty, setTradeQty] = useState('');
  const [tradePrice, setTradePrice] = useState('');
  const [tradePosId, setTradePosId] = useState('');"""
content = content.replace("  const [activeTab, setActiveTab] = useState<'portfolio' | 'committee' | 'ledger'>('portfolio');", state_vars)

# Add handleManualTrade function
handle_trade = """  const handleManualTrade = async () => {
    try {
      if (tradeType === 'NEW') {
        const res = await fetch('/api/cai/portfolio/positions', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ symbol: tradeSymbol, quantity: Number(tradeQty), average_price: Number(tradePrice) })
        });
        if (!res.ok) {
           const err = await res.json();
           throw new Error(err.detail || 'Failed to add position');
        }
      } else {
        const res = await fetch(`/api/cai/portfolio/positions/${tradePosId}/tranches`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ quantity: Number(tradeQty), entry_price: Number(tradePrice) })
        });
        if (!res.ok) {
           const err = await res.json();
           throw new Error(err.detail || 'Failed to add tranche');
        }
      }
      setShowManualTrade(false);
      setTradeSymbol(''); setTradeQty(''); setTradePrice(''); setTradePosId('');
      fetchPortfolio();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const fetchPortfolio = async () => {"""
content = content.replace("  const fetchPortfolio = async () => {", handle_trade)

# Add button above table
table_header = """      {activeTab === 'portfolio' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="flex justify-between items-center p-4 border-b border-gray-800 bg-gray-800/20">
            <h2 className="text-lg font-bold text-white">Active Positions</h2>
            <button 
              onClick={() => setShowManualTrade(true)}
              className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              + Manual Trade Entry
            </button>
          </div>
        <table className="w-full text-left border-collapse">"""
content = content.replace("""      {activeTab === 'portfolio' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-left border-collapse">""", table_header)

# Add Modal JSX at the end
modal_jsx = """      {showManualTrade && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 w-full max-w-md p-6 rounded-2xl border border-gray-700 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Manual Trade Entry</h3>
            
            <div className="flex gap-4 mb-4">
              <label className="flex items-center text-gray-300">
                <input type="radio" checked={tradeType === 'NEW'} onChange={() => setTradeType('NEW')} className="mr-2" />
                New Position
              </label>
              <label className="flex items-center text-gray-300">
                <input type="radio" checked={tradeType === 'TRANCHE'} onChange={() => setTradeType('TRANCHE')} className="mr-2" />
                Add Tranche
              </label>
            </div>

            {tradeType === 'NEW' && (
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Symbol</label>
                <input type="text" className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white" value={tradeSymbol} onChange={e => setTradeSymbol(e.target.value.toUpperCase())} placeholder="e.g. LENSKART" />
              </div>
            )}

            {tradeType === 'TRANCHE' && (
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Select Position</label>
                <select className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white" value={tradePosId} onChange={e => setTradePosId(e.target.value)}>
                  <option value="">-- Select Active Position --</option>
                  {portfolio?.positions?.map((p: any) => (
                    <option key={p.id} value={p.id}>{p.symbol} (Tranche {p.tranche}/10)</option>
                  ))}
                </select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Quantity</label>
                <input type="number" className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white" value={tradeQty} onChange={e => setTradeQty(e.target.value)} />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Price (₹)</label>
                <input type="number" className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white" value={tradePrice} onChange={e => setTradePrice(e.target.value)} />
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <button className="px-4 py-2 text-gray-400 hover:text-white" onClick={() => setShowManualTrade(false)}>Cancel</button>
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium" onClick={handleManualTrade}>
                Execute Trade
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
"""
content = content.replace("    </div>\n  );\n};\n", modal_jsx)

with open("frontend/src/CaiPortfolioPage.tsx", "w") as f:
    f.write(content)
