import { useState, useEffect } from 'react';

export default function DarvasScreener() {
  const [data, setData] = useState<{ scan_name: string, total_count: number, results: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/v1/screener/darvas', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('mri_auth_token')}`
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
        'Authorization': `Bearer ${localStorage.getItem('mri_auth_token')}`
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
        <div style={{ display: 'grid', gap: '16px', marginTop: '16px' }}>
          {data.results.map((r, i) => (
            <div key={i} style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '18px', fontWeight: 'bold' }}>{r.symbol}</span>
                <span style={{ color: '#94a3b8' }}>{r.company_name}</span>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '12px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>Close Price</div>
                  <div>₹{r.close?.toFixed(2)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>Market Cap</div>
                  <div>₹{r.market_cap_cr?.toFixed(0)} Cr</div>
                </div>
              </div>

              <div style={{ borderTop: '1px solid #1e293b', paddingTop: '12px' }}>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>Why it passed:</div>
                {r.explanation.map((exp: string, idx: number) => (
                  <div key={idx} style={{ fontSize: '13px', color: '#22c55e' }}>{exp}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
