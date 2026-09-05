import { useState, useEffect } from 'react';

export default function PreBreakoutPage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // We'll add this endpoint to the api client
    fetch('/api/v1/screener/pre-breakout', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
      .then(res => res.json())
      .then(json => {
        if (json.error) throw new Error(json.error);
        setData(json);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-center text-gray-400">Scanning market for setups...</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 className="page-title">Pre-Breakout Scanner</h1>
        <p style={{ color: '#94a3b8', marginTop: '8px' }}>
          Finding stocks in a strong bullish trend, near 52W highs, with healthy momentum (RSI 55-70).
          <br/>
          {data?.total_count} candidates found for {data?.last_updated}.
        </p>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>SYMBOL</th>
              <th style={{ textAlign: 'right' }}>CLOSE</th>
              <th style={{ textAlign: 'right' }}>52W HIGH</th>
              <th style={{ textAlign: 'right' }}>% OFF HIGH</th>
              <th style={{ textAlign: 'right' }}>EMA 20</th>
              <th style={{ textAlign: 'right' }}>% FROM 20EMA</th>
              <th style={{ textAlign: 'right' }}>RSI 14</th>
            </tr>
          </thead>
          <tbody>
            {data?.results?.map((row: any) => {
              const pctOffHigh = ((row.high - row.close) / row.high) * 100;
              const pctFromEma20 = ((row.close - row.ema_20) / row.ema_20) * 100;

              return (
                <tr 
                  key={row.symbol} 
                  className="clickable-row"
                  onClick={() => onSelectStock({ symbol: row.symbol })}
                >
                  <td style={{ fontWeight: 600, color: '#f8fafc' }}>{row.symbol}</td>
                  <td style={{ textAlign: 'right' }}>₹{row.close.toFixed(2)}</td>
                  <td style={{ textAlign: 'right' }}>₹{row.high.toFixed(2)}</td>
                  <td style={{ textAlign: 'right', color: '#fbbf24' }}>{pctOffHigh.toFixed(2)}%</td>
                  <td style={{ textAlign: 'right' }}>₹{row.ema_20.toFixed(2)}</td>
                  <td style={{ textAlign: 'right', color: '#22c55e' }}>{pctFromEma20.toFixed(2)}%</td>
                  <td style={{ textAlign: 'right' }}>{row.rsi_14.toFixed(2)}</td>
                </tr>
              );
            })}
            {data?.results?.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '24px' }}>No setups found matching criteria.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
