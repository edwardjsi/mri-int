// @ts-nocheck
import { useState } from 'react';
import { api } from './api';

/**
 * SparklineTimeline — tiny inline SVG showing confidence, hedging, transparency
 * across the last N quarters. No external deps.
 */
function SparklineTimeline({ timeline }) {
  const W = 320, H = 70, PAD = 4;
  const dims = [
    { key: 'confidence',   color: '#4ade80', label: 'Confidence' },
    { key: 'hedging',      color: '#fbbf24', label: 'Hedging' },
    { key: 'transparency', color: '#60a5fa', label: 'Transparency' },
  ];
  const xs = timeline.map((_, i) => PAD + (i * (W - 2 * PAD)) / Math.max(1, timeline.length - 1));
  const yFor = (v: number) => H - PAD - v * (H - 2 * PAD);
  return (
    <div>
      <svg width={W} height={H} style={{display:'block',width:'100%',maxWidth:320}}>
        {/* gridline at 50% */}
        <line x1={PAD} x2={W - PAD} y1={H/2} y2={H/2} stroke="#1f2937" strokeWidth={1} strokeDasharray="2 3"/>
        {dims.map(d => (
          <polyline
            key={d.key}
            fill="none"
            stroke={d.color}
            strokeWidth={1.5}
            points={timeline.map((row, i) => `${xs[i]},${yFor(Number(row[d.key] || 0))}`).join(' ')}
          />
        ))}
        {timeline.map((row, i) => (
          <circle key={i} cx={xs[i]} cy={yFor(Number(row.confidence || 0))} r={2.5} fill="#4ade80"/>
        ))}
      </svg>
      <div style={{display:'flex',gap:12,marginTop:4,fontSize:'0.65rem'}}>
        {dims.map(d => (
          <span key={d.key} style={{color:'#94a3b8'}}>
            <span style={{display:'inline-block',width:8,height:8,background:d.color,borderRadius:'50%',marginRight:4,verticalAlign:'middle'}}/>
            {d.label}
          </span>
        ))}
        <span style={{color:'#475569',marginLeft:'auto'}}>
          {timeline[0]?.quarter_label} → {timeline[timeline.length - 1]?.quarter_label}
        </span>
      </div>
    </div>
  );
}

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
          {cls === 'pending' && p.status === 'UNABLE_TO_VERIFY' && p.unable_reason && (
            <span title={p.unable_reason} style={{
              marginLeft:'auto', cursor:'help',
              background:'#1e293b', color:'#fbbf24',
              padding:'2px 8px', borderRadius:10, fontSize:'0.65rem',
              fontWeight:600, border:'1px dashed #f59e0b',
            }}>
              ℹ️ why?
            </span>
          )}
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
            <div style={{background:'#0d1421',border:'1px solid #1a2236',borderRadius:10,padding:'14px 18px',marginBottom:20,color:'#475569',fontSize:'0.85rem'}}>
              <div style={{fontWeight:600,color:'#94a3b8',marginBottom:6}}>
                ⏳ No verified promises yet — {report.total_unable || 0} of {(report.pending||[]).length} pending couldn't be matched to financials.
              </div>
              {report.guidance_quality_signal === 'DIRECTIONAL ONLY' && (
                <div style={{fontSize:'0.78rem',color:'#fbbf24'}}>
                  ⚠️ This management team gives directional / qualitative guidance only — they don't typically commit to numbers. Verification requires numeric targets.
                </div>
              )}
              {report.all_future_promises && report.dominant_guidance_type && (
                <div style={{fontSize:'0.78rem',color:'#64748b',marginTop:4}}>
                  Most-frequent topic: <b style={{color:'#94a3b8'}}>{report.dominant_guidance_type}</b>. Future quarters will verify as results land.
                </div>
              )}
            </div>
          )}

          {/* Header metadata band: transcript coverage + guidance quality */}
          {(report.transcript_count > 0 || report.total_promises_extracted > 0) && (
            <div style={{display:'flex',flexWrap:'wrap',gap:8,marginBottom:16,fontSize:'0.72rem',alignItems:'center'}}>
              <span style={{background:'#1e293b',color:'#cbd5e1',padding:'4px 10px',borderRadius:14,fontWeight:600}}>
                📊 {report.transcript_count} transcript{report.transcript_count !== 1 ? 's' : ''} analyzed
                {report.transcript_date_range?.earliest && report.transcript_date_range?.latest && (
                  <span style={{color:'#64748b',marginLeft:6,fontWeight:400}}>
                    · {report.transcript_date_range.earliest} → {report.transcript_date_range.latest}
                  </span>
                )}
              </span>
              <span style={{background:'#1e293b',color:'#cbd5e1',padding:'4px 10px',borderRadius:14,fontWeight:600}}>
                {report.total_promises_extracted} promises extracted
              </span>
              <span style={{background: report.numerical_guidance_pct < 30 ? '#7f1d1d' : report.numerical_guidance_pct < 70 ? '#451a03' : '#14532d',
                           color: report.numerical_guidance_pct < 30 ? '#fca5a5' : report.numerical_guidance_pct < 70 ? '#fbbf24' : '#4ade80',
                           padding:'4px 10px',borderRadius:14,fontWeight:600}}>
                {report.numerical_guidance_pct}% numerical guidance
              </span>
              {report.dominant_guidance_type && (
                <span style={{background:'#1e293b',color:'#94a3b8',padding:'4px 10px',borderRadius:14,fontWeight:600}}>
                  🎯 Dominant: {report.dominant_guidance_type}
                </span>
              )}
              {report.guidance_quality_signal === 'DIRECTIONAL ONLY' && (
                <span style={{background:'#1e3a8a',color:'#60a5fa',padding:'4px 10px',borderRadius:14,fontWeight:700,letterSpacing:'0.04em'}}>
                  📐 DIRECTIONAL ONLY
                </span>
              )}
            </div>
          )}

          {/* Intonation section — 9-dim management tone */}
          {report.intonation?.latest && report.intonation.quarters_observed >= 1 && (
            <div style={{background:'#0d1421',border:'1px solid #1a2236',borderRadius:10,padding:'14px 18px',marginBottom:20}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:10}}>
                <div>
                  <div style={{fontSize:'0.7rem',fontWeight:700,textTransform:'uppercase',letterSpacing:'0.07em',color:'#94a3b8'}}>
                    🎙️ Management Tone — {report.intonation.latest.quarter_label}
                  </div>
                  <div style={{fontSize:'0.85rem',color:'#cbd5e1',marginTop:4,lineHeight:1.5}}>
                    {report.intonation.latest.summary || '—'}
                  </div>
                  {report.intonation.latest.headwinds_named && report.intonation.latest.headwinds_named.length > 0 && (
                    <div style={{fontSize:'0.72rem',color:'#94a3b8',marginTop:6}}>
                      <b style={{color:'#fbbf24'}}>Headwinds named:</b> {report.intonation.latest.headwinds_named.join(' · ')}
                    </div>
                  )}
                </div>
                {report.intonation.tone_shift_detected && (
                  <div style={{background:'#1e3a8a',color:'#60a5fa',padding:'4px 10px',borderRadius:12,fontSize:'0.7rem',fontWeight:700,letterSpacing:'0.04em',whiteSpace:'nowrap'}}>
                    🚨 TONE SHIFT
                  </div>
                )}
              </div>

              {/* 9-dimension bar grid */}
              <div style={{display:'grid',gridTemplateColumns:'repeat(3, 1fr)',gap:'8px 16px',marginTop:12}}>
                {[
                  ['Confidence',      report.intonation.latest.confidence,     '#4ade80'],
                  ['Hedging',         report.intonation.latest.hedging,        '#fbbf24'],
                  ['Aggression',      report.intonation.latest.aggression,     '#f87171'],
                  ['Transparency',    report.intonation.latest.transparency,   '#60a5fa'],
                  ['Optimism',        report.intonation.latest.optimism,       '#4ade80'],
                  ['Pessimism',       report.intonation.latest.pessimism,      '#94a3b8'],
                  ['Accountability',  report.intonation.latest.accountability, '#a78bfa'],
                  ['Numerical density', report.intonation.latest.numerical_density, '#22d3ee'],
                ].map(([label, val, color]) => {
                  const v = Number(val || 0);
                  const pct = Math.round(v * 100);
                  const delta = report.intonation.previous
                    ? (v - (report.intonation.previous[String(label).toLowerCase().replace(' ', '_')] ?? 0))
                    : 0;
                  const arrow = delta > 0.01 ? ' ↑' : delta < -0.01 ? ' ↓' : '';
                  return (
                    <div key={String(label)} style={{display:'flex',flexDirection:'column',gap:3}}>
                      <div style={{display:'flex',justifyContent:'space-between',fontSize:'0.68rem'}}>
                        <span style={{color:'#94a3b8'}}>{label as string}</span>
                        <span style={{color: color as string, fontWeight:700}}>{pct}{arrow}</span>
                      </div>
                      <div style={{height:4,background:'#1f2937',borderRadius:2,overflow:'hidden'}}>
                        <div style={{height:'100%',width:`${pct}%`,background: color as string,transition:'width 0.5s'}}/>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Quarter timeline sparkline — show confidence + hedging over time */}
              {report.intonation.timeline && report.intonation.timeline.length >= 2 && (
                <div style={{marginTop:14,borderTop:'1px solid #1a2236',paddingTop:10}}>
                  <div style={{fontSize:'0.68rem',color:'#64748b',textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:6,fontWeight:700}}>
                    Tone trajectory
                  </div>
                  <SparklineTimeline timeline={report.intonation.timeline} />
                </div>
              )}
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