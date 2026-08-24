import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

export default function DarvasScreener() {
  const [data, setData] = useState<{ scan_name: string, total_count: number, results: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const [chartData, setChartData] = useState<any[] | null>(null);
  const [chartLoading, setChartLoading] = useState(false);

  useEffect(() => {
    fetch('/api/v1/screener/darvas', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('mri_token')}`
      }
    })
    .then(res => {
      if (!res.ok) throw new Error("Failed to fetch Darvas scan");
      return res.json();
    })
    .then(resData => {
      setData(resData);
      setLoading(false);
    })
    .catch(err => {
      setError(err.message);
      setLoading(false);
    });
  }, []);

  const handleSaveScan = () => {
    fetch('/api/v1/screener/save_scan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('mri_token')}`
      },
      body: JSON.stringify({ name: "Daily Darvas Scan" })
    })
    .then(res => res.json())
    .then(resData => {
      if (resData.status === 'success') {
        alert("Scan saved successfully!");
      } else {
        alert("Failed to save scan: " + resData.error);
      }
    })
    .catch(() => alert("Error saving scan"));
  };

  const handleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const toggleChart = (symbol: string) => {
    if (expandedSymbol === symbol) {
      setExpandedSymbol(null);
      setChartData(null);
      return;
    }
    setExpandedSymbol(symbol);
    setChartLoading(true);
    fetch(`/api/v1/screener/chart/${symbol}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('mri_token')}`
      }
    })
    .then(res => res.json())
    .then(resData => {
      setChartData(resData.data);
      setChartLoading(false);
    })
    .catch(() => {
      setChartLoading(false);
    });
  };

  const sortedResults = data?.results ? [...data.results].sort((a, b) => {
    if (!sortConfig) return 0;
    if (a[sortConfig.key] < b[sortConfig.key]) {
      return sortConfig.direction === 'asc' ? -1 : 1;
    }
    if (a[sortConfig.key] > b[sortConfig.key]) {
      return sortConfig.direction === 'asc' ? 1 : -1;
    }
    return 0;
  }) : [];

  if (loading) return <div className="p-4" style={{ color: 'white' }}>Loading Darvas Screener...</div>;
  if (error) return <div className="p-4" style={{ color: 'red' }}>Error: {error}</div>;
  if (!data) return null;

  return (
    <div style={{ padding: '24px', color: 'white', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>{data.scan_name}</h2>
        <button 
          onClick={handleSaveScan}
          style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}
        >
          Save Scan
        </button>
      </div>

      <div style={{ marginBottom: '24px', background: '#1e293b', padding: '16px', borderRadius: '8px' }}>
        <h3>Conditions</h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0 0' }}>
          <li>✓ Universe: NIFTY 500</li>
          <li>✓ Market Cap &gt; ₹800 Cr</li>
          <li>✓ Daily Close &gt; ₹50</li>
          <li>✓ Daily High = 252-day Maximum Daily High</li>
        </ul>
      </div>

      <div>
        <h3>Results: {data.total_count} stocks</h3>
        <div style={{ marginTop: '16px', overflowX: 'auto', maxHeight: 'calc(100vh - 300px)', overflowY: 'auto', background: '#0f172a', borderRadius: '8px', border: '1px solid #334155' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155' }}>
                <th style={{ padding: '12px', cursor: 'pointer', color: '#94a3b8' }} onClick={() => handleSort('symbol')}>Symbol {sortConfig?.key === 'symbol' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
                <th style={{ padding: '12px', cursor: 'pointer', color: '#94a3b8' }} onClick={() => handleSort('company_name')}>Name {sortConfig?.key === 'company_name' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
                <th style={{ padding: '12px', cursor: 'pointer', color: '#94a3b8' }} onClick={() => handleSort('close')}>Close {sortConfig?.key === 'close' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
                <th style={{ padding: '12px', cursor: 'pointer', color: '#94a3b8' }} onClick={() => handleSort('market_cap_cr')}>Mcap (Cr) {sortConfig?.key === 'market_cap_cr' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
              </tr>
            </thead>
            <tbody>
              {sortedResults.map((r, i) => (
                <React.Fragment key={i}>
                  <tr style={{ borderBottom: '1px solid #1e293b' }}>
                    <td style={{ padding: '12px', color: '#3b82f6', cursor: 'pointer', fontWeight: 'bold' }} onClick={() => toggleChart(r.symbol)}>{r.symbol}</td>
                    <td style={{ padding: '12px' }}>{r.company_name}</td>
                    <td style={{ padding: '12px' }}>₹{r.close?.toFixed(2)}</td>
                    <td style={{ padding: '12px' }}>₹{r.market_cap_cr?.toFixed(0)}</td>
                  </tr>
                  {expandedSymbol === r.symbol && (
                    <tr>
                      <td colSpan={4} style={{ padding: '16px', background: '#1e293b' }}>
                        <div style={{ fontSize: '14px', marginBottom: '12px', color: '#22c55e' }}>
                           {r.explanation.map((e: string, idx: number) => <div key={idx}>{e}</div>)}
                        </div>
                        <div style={{ height: '300px', width: '100%' }}>
                          {chartLoading ? <div>Loading chart...</div> : 
                           chartData && chartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                <XAxis dataKey="date" stroke="#94a3b8" tickFormatter={(t) => t.substring(5)} />
                                <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                                <Line type="monotone" dataKey="close" stroke="#3b82f6" dot={false} strokeWidth={2} />
                              </LineChart>
                            </ResponsiveContainer>
                          ) : (
                            <div>No chart data available.</div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
