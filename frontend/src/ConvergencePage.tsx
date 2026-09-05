import { useState, useEffect } from 'react';

export default function ConvergencePage({ onSelectStock }: { onSelectStock: (stock: any) => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/api/v1/screener/convergence', {
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

  if (loading) return <div className="p-8 text-center text-gray-400">Aggregating signals and looking for convergence...</div>;
  if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '8px' }}>Signal Convergence (3+ Overlaps)</h2>
        <p style={{ color: '#94a3b8' }}>
          Found {data?.convergence_count} stocks appearing in 3 or more signals (out of {data?.total_scanned} scanned).
        </p>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>SYMBOL</th>
              <th style={{ textAlign: 'center' }}>SIGNAL COUNT</th>
              <th>CONVERGING SIGNALS</th>
            </tr>
          </thead>
          <tbody>
            {data?.results?.map((row: any) => (
              <tr 
                key={row.symbol} 
                className="clickable-row"
                onClick={() => onSelectStock({ symbol: row.symbol })}
              >
                <td style={{ fontWeight: 600, color: '#f8fafc', width: '150px' }}>{row.symbol}</td>
                <td style={{ textAlign: 'center', width: '120px' }}>
                  <span style={{
                    background: row.count >= 4 ? '#22c55e20' : '#3b82f620',
                    color: row.count >= 4 ? '#22c55e' : '#3b82f6',
                    padding: '4px 10px',
                    borderRadius: '12px',
                    fontWeight: 'bold',
                    fontSize: '14px'
                  }}>
                    {row.count} / 5
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {row.signals.map((sig: str) => (
                      <span key={sig} style={{
                        background: '#334155',
                        color: '#cbd5e1',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        border: '1px solid #475569'
                      }}>
                        {sig}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {data?.results?.length === 0 && (
              <tr>
                <td colSpan={3} style={{ textAlign: 'center', padding: '24px' }}>No stocks currently converging across 3 or more signals.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
