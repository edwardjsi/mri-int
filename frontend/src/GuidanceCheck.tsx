// @ts-nocheck
import { useState } from 'react';
import { api } from './api';

function toast(msg, isError=false) {
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:24px;right:24px;background:#111827;border:1px solid ${isError?'#ef4444':'#22c55e'};color:${isError?'#f87171':'#4ade80'};padding:12px 20px;border-radius:10px;font-size:0.85rem;font-weight:600;z-index:999;transition:opacity 0.3s`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3500);
}

export default function GuidanceCheck() {
  const [symbol, setSymbol] = useState('');
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const load = async (sym: string) => {
    if (!sym.trim()) return;
    setLoading(true); setError(''); setReport(null);
    try {
      const data = await api.getGuidanceReport(sym.toUpperCase());
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load report');
    }
    setLoading(false);
  };

  const send = async () => {
    if (!symbol.trim() || !report) return;
    setSending(true);
    try {
      await api.sendGuidanceEmail(symbol.toUpperCase());
      toast(`📧 Report sent! Check your inbox.`);
    } catch (e: any) {
      // apiFetch throws on non-2xx; the error message includes the status text
      toast(`Failed: ${e.message || 'Unknown error'}`, true);
    }
    setSending(false);
  };

  const { achieved=[], missed=[], partial=[], pending=[] } = report || {};

  // Accuracy ring
  const accuracy = report?.accuracy_pct || 0;
  const circumference = 2 * Math.PI * 36;
  const ringOffset = circumference - (accuracy / 100) * circumference;
  const ringColor = accuracy >= 70 ? '#4ade80' : accuracy >= 40 ? '#fbbf24' : accuracy > 0 ? '#f87171' : '#3b82f6';

  const verdictClass = { WATCHING:'verdict-watching','ADD ZONE':'verdict-add','HOLD ZONE':'verdict-hold','REDUCE ZONE':'verdict-reduce','THESIS BROKEN':'verdict-broken' }[report?.verdict] || 'verdict-watching';

  function promiseItem(p: any, cls: string) {
    const meta = [];
    if (p.target) meta.push(<span style={{background:'#1e293b',color:'#94a3b8',padding:'1px 6px',borderRadius:3,fontSize:'0.68rem',marginRight:6}}>🎯 {p.target}</span>);
    if (p.deadline) meta.push(<span style={{color:'#94a3b8'}}>📅 {p.deadline}</span>);
    if (p.verified_period) meta.push(<span style={{color:'#475569'}}>{p.verified_period}</span>);

    const actualHtml = p.actual ? (
      <div style={{marginTop:6,fontSize:'0.82rem'}}>
        <span style={{color:'#94a3b8'}}>Actual:</span>
        <span style={{fontWeight:600,marginLeft:4,color: cls==='missed'?'#f87171':'#4ade80'}}>{p.actual}</span>
        {p.variance_pct != null && <span style={{color:'#64748b',marginLeft:6}}>({p.variance_pct>0?'+':''}{p.variance_pct.toFixed(1)}%)</span>}
      </div>
    ) : null;

    return (
      <div key={p.promise} style={{background:'#0f172a',borderRadius:8,padding:'12px 14px',marginBottom:8,borderLeft:`3px solid ${cls==='achieved'?'#22c55e':cls==='missed'?'#ef4444':cls==='partial'?'#f59e0b':'#3b82f6'}`}}>
        <div style={{fontSize:'0.875rem',lineHeight:1.45,marginBottom:6}}>{p.promise}</div>
        <div style={{display:'flex',gap:12,flexWrap:'wrap',fontSize:'0.72rem',color:'#64748b',alignItems:'center'}}>
          <span style={{background:'#1e293b',color:'#94a3b8',padding:'1px 6px',borderRadius:3,fontSize:'0.68rem'}}>{p.type}</span>
          {meta}
          {actualHtml}
        </div>
      </div>
    );
  }

  function section(label: string, cls: string, items: any[]) {
    if (!items.length) return null;
    const colors: Record<string,string> = { achieved:'#4ade80', missed:'#f87171', partial:'#fbbf24', pending:'#60a5fa' };
    const borders: Record<string,string> = { achieved:'#14532d', missed:'#450a0a', partial:'#451a03', pending:'#1e3a5f' };
    return (
      <div style={{marginTop:16}}>
        <div style={{fontSize:'0.72rem',fontWeight:700,textTransform:'uppercase',letterSpacing:'0.07em',padding:'5px 0',borderBottom:`1px solid ${borders[cls]}`,color:colors[cls],marginBottom:8}}>
          {cls==='achieved'?'✅ Kept':cls==='missed'?'❌ Broken':cls==='partial'?'⚠️ Partial':'⏳ Upcoming'} — {items.length}
        </div>
        {items.map(p => promiseItem(p, cls))}
      </div>
    );
  }

  return (
    <div style={{padding:'20px',color:'#e2e8f0',maxWidth:700,margin:'0 auto'}}>
      <h2 style={{fontSize:'1.3rem',fontWeight:800,marginBottom:4}}>🔍 GuidanceCheck</h2>
      <p style={{color:'#64748b',fontSize:'0.8rem',marginBottom:16}}>Management Credibility Report — promises kept vs broken</p>

      <div style={{display:'flex',gap:10,flexWrap:'wrap',marginBottom:20}}>
        <input
          value={symbol}
          onChange={e => setSymbol(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && load(symbol)}
          placeholder="Symbol (e.g. TCS, INFY)"
          style={{background:'#1e293b',border:'1px solid #334155',borderRadius:6,padding:'8px 12px',color:'#e2e8f0',width:160,outline:'none',fontSize:'0.9rem'}}
        />
        <button onClick={() => load(symbol)} disabled={loading}
          style={{background:'#2563eb',color:'#fff',border:'none',borderRadius:6,padding:'8px 16px',cursor:'pointer',fontWeight:600,opacity:loading?0.5:1}}>
          {loading ? '…' : 'Check'}
        </button>
        {report && (
          <button onClick={send} disabled={sending}
            style={{background:'#14532d',color:'#4ade80',border:'1px solid #166534',borderRadius:6,padding:'8px 16px',cursor:'pointer',fontWeight:600,opacity:sending?0.6:1,display:'flex',alignItems:'center',gap:6}}>
            📧 {sending ? 'Sending…' : 'Send Report'}
          </button>
        )}
      </div>

      {error && <div style={{padding:10,background:'#7f1d1d20',border:'1px solid #ef444440',borderRadius:6,color:'#fca5a5',marginBottom:12,fontSize:'0.85rem'}}>{error}</div>}

      {loading && <div style={{textAlign:'center',padding:32,color:'#475569'}}>Loading report…</div>}

      {report && (
        <div style={{background:'#111827',border:'1px solid #1f2937',borderRadius:14,padding:24}}>
          {/* Header */}
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',flexWrap:'wrap',gap:16,marginBottom:20}}>
            <div>
              <h3 style={{fontSize:'1.6rem',fontWeight:800,margin:0}}>{report.symbol}</h3>
              <div style={{color:'#64748b',fontSize:'0.78rem',marginTop:2}}>{report.report_date} · {report.total_material} trackable promises</div>
            </div>
            <div style={{textAlign:'right'}}>
              <div style={{background:verdictClass==='verdict-watching'?'#1e293b':verdictClass==='verdict-add'?'#14532d':verdictClass==='verdict-hold'?'#451a03':verdictClass==='verdict-reduce'?'#7f1d1d':'#500',color:verdictClass==='verdict-watching'?'#94a3b8':verdictClass==='verdict-add'?'#4ade80':verdictClass==='verdict-hold'?'#fbbf24':verdictClass==='verdict-reduce'?'#f87171':'#fff',fontSize:'0.75rem',fontWeight:700,padding:'6px 14px',borderRadius:20,textTransform:'uppercase',letterSpacing:'0.06em',display:'inline-block'}}>
                {report.verdict}
              </div>
            </div>
          </div>

          {/* Accuracy bar */}
          {(report.total_verified || 0) > 0 ? (
            <div style={{background:'#0d1421',border:'1px solid #1a2236',borderRadius:10,padding:'14px 18px',marginBottom:20,display:'flex',gap:20,alignItems:'center',flexWrap:'wrap'}}>
              <div style={{width:64,height:64,flexShrink:0,position:'relative'}}>
                <svg width="64" height="64" viewBox="0 0 64 64" style={{transform:'rotate(-90deg)'}}>
                  <circle cx="32" cy="32" r="26" fill="none" stroke="#1f2937" strokeWidth="6"/>
                  <circle cx="32" cy="32" r="26" fill="none" stroke={ringColor} strokeWidth="6"
                    strokeDasharray={circumference} strokeDashoffset={ringOffset} strokeLinecap="round"
                    style={{transition:'stroke-dashoffset 1s ease'}}/>
                </svg>
                <div style={{position:'absolute',inset:0,display:'flex',alignItems:'center',justifyContent:'center',fontSize:'0.85rem',fontWeight:700,color:verdictClass.includes('add')?'#4ade80':verdictClass.includes('hold')?'#fbbf24':verdictClass.includes('reduce')?'#f87171':'#e2e8f0'}}>
                  {accuracy > 0 ? `${accuracy.toFixed(0)}%` : '—'}
                </div>
              </div>
              <div style={{flex:1}}>
                <div style={{display:'flex',gap:12,fontSize:'0.82rem',marginBottom:4}}>
                  <span style={{color:'#4ade80'}}>✅ {achieved.length} Kept</span>
                  <span style={{color:'#ef4444'}}>❌ {missed.length} Broken</span>
                  <span style={{color:'#fbbf24'}}>⚠️ {partial.length} Partial</span>
                </div>
                <div style={{display:'flex',gap:12,fontSize:'0.8rem',color:'#64748b'}}>
                  <span>⏳ {(report.pending||[]).length} Pending</span>
                  {report.credibility?.trend && <span>· {report.credibility.trend}</span>}
                </div>
              </div>
            </div>
          ) : (
            <div style={{background:'#0d1421',border:'1px solid #1a2236',borderRadius:10,padding:'14px 18px',marginBottom:20,color:'#475569',fontSize:'0.85rem',textAlign:'center'}}>
              ⏳ No verified promises yet — {(report.pending||[]).length} pending. Run <b>⚡ Prime All Stocks</b> to trigger verification against quarterly financials.
            </div>
          )}

          {/* Promise sections */}
          {section('✅ Kept', 'achieved', achieved)}
          {section('❌ Broken', 'missed', missed)}
          {section('⚠️ Partial', 'partial', partial)}
          {section('⏳ Upcoming', 'pending', (report.pending||[]).slice(0, 8))}
          {(report.pending||[]).length > 8 && (
            <div style={{color:'#475569',fontSize:'0.78rem',marginTop:8,padding:'0 4px'}}>+{report.pending.length - 8} more pending promises — click Check to see all</div>
          )}
        </div>
      )}

      {!report && !loading && !error && (
        <div style={{textAlign:'center',padding:40,color:'#475569',fontSize:'0.88rem'}}>
          Enter a symbol to see the management credibility report.<br/>
          Only promises with numeric targets and defined deadlines are shown.
        </div>
      )}
    </div>
  );
}