import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ModelBadgeGroup } from './components/ModelBadge';

const EvidenceQuote = ({ quote, source }: { quote: string, source: string }) => (
  <div className="mt-1 text-xs text-slate-400 italic border-l-2 border-slate-600 pl-2 py-0.5 bg-slate-800/30">
    "{quote}" — <span className="text-slate-500">{source}</span>
  </div>
);

export const CompanyDossier = () => {
  const { symbol = 'GRANULES' } = useParams();
  const [activeTab, setActiveTab] = useState('business');
  
  const [intelligence, setIntelligence] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchIntelligence = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/ciw/${symbol}`);
        if (!res.ok) {
          if (res.status === 404) {
            setIntelligence(null);
          } else {
            throw new Error('Failed to load company intelligence');
          }
        } else {
          const data = await res.json();
          setIntelligence(data);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchIntelligence();
  }, [symbol]);

  if (loading) {
    return <div className="min-h-screen bg-slate-900 text-slate-200 p-8">Loading dossier...</div>;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-200 p-8">
        <div className="bg-rose-900/50 border border-rose-500/50 text-rose-400 p-4 rounded-lg">
          <h2 className="font-bold mb-2">Error loading dossier</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  // Graceful degradation when we have models but missing knowledge, or completely missing
  const hasKnowledge = intelligence && intelligence.knowledge_status > 0;
  const models = intelligence?.models || [];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <header className="mb-6 border-b border-slate-700 pb-4 flex justify-between items-end">
          <div>
            <h1 className="text-sm text-slate-400 uppercase tracking-widest">Investment Dossier v1.0</h1>
          </div>
        </header>

        {/* Sticky Investment Summary */}
        <section className="sticky top-4 z-10 mb-8 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-lg p-6 shadow-2xl">
          <div className="flex justify-between items-start mb-4 border-b border-slate-800 pb-4">
            <div>
                <h2 className="text-2xl font-bold text-white tracking-tight">{symbol}</h2>
                <div className="mt-3">
                    <ModelBadgeGroup models={models} />
                </div>
            </div>
            
            {/* Intelligence Status Panel */}
            <div className="flex flex-col items-end text-xs">
              <span className="text-slate-400 uppercase tracking-wider mb-2 font-semibold">Intelligence Status</span>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-right">
                <span className="text-slate-500">Knowledge:</span>
                <span className="text-emerald-400 font-medium">{intelligence?.knowledge_status || 0}%</span>
                
                <span className="text-slate-500">Models:</span>
                <span className="text-slate-300">{models.length > 0 ? `${models.length} Active` : 'None'}</span>
                
                <span className="text-slate-500">Last Compiled:</span>
                <span className="text-slate-300">
                  {intelligence?.freshness?.knowledge ? new Date(intelligence.freshness.knowledge).toLocaleDateString() : 'Never'}
                </span>
              </div>
            </div>
          </div>

          {!hasKnowledge && (
            <div className="mb-2">
              <div className="bg-slate-800/50 border border-amber-900/50 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <h3 className="text-amber-400 font-semibold mb-1">Knowledge Not Compiled</h3>
                  <p className="text-slate-400 text-sm">We don't have MOSI compiled facts for {symbol} yet.</p>
                </div>
                <button className="bg-amber-600/20 hover:bg-amber-600/40 text-amber-500 border border-amber-600/50 px-4 py-2 rounded text-sm transition-colors">
                  Compile MOSI
                </button>
              </div>
            </div>
          )}

          {hasKnowledge && (
            <>
              <div className="mb-5 pb-5 border-b border-slate-800">
                <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2">Can I explain this company in 30 seconds? <span className="text-emerald-400 ml-1">YES</span></div>
                <p className="text-slate-200 text-base leading-relaxed font-medium">
                  {intelligence?.business?.what_it_does || 'Business summary not available.'}
                </p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-4">
                  <div>
                    <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2">Investment Thesis</div>
                    <ul className="text-slate-200 text-sm leading-relaxed space-y-1">
                      {intelligence?.business?.competitive_advantage?.map((adv: string, i: number) => (
                        <li key={i}>• {adv}</li>
                      )) || <li className="text-slate-500">Not enough evidence</li>}
                    </ul>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Biggest catalyst</div>
                      <div className="text-emerald-400 text-sm font-medium mb-1">
                        {intelligence?.growth?.drivers?.[0]?.category || 'Unknown'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Biggest risk</div>
                      <div className="text-rose-400 text-sm font-medium mb-1">
                         Risk tracking coming soon
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </section>

        {/* Tabs */}
        <div className="flex flex-wrap gap-2 mb-6 border-b border-slate-800 pb-px">
          {['Overview', 'Business', 'Growth', 'Risks', 'Management', 'Decision', 'Financials', 'Technical', 'Documents'].map(tab => {
            const tabKey = tab.toLowerCase();
            return (
              <button 
                key={tabKey}
                className={`px-4 py-2 font-medium transition-colors ${activeTab === tabKey ? 'border-b-2 border-emerald-500 text-emerald-400' : 'text-slate-500 hover:text-slate-300'}`}
                onClick={() => setActiveTab(tabKey)}
              >
                {tab}
              </button>
            );
          })}
        </div>

        {activeTab === 'business' && hasKnowledge && (
          <section className="mb-8 bg-slate-800/50 rounded-lg p-6 border border-slate-700 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <h2 className="text-xl font-bold text-slate-100 mb-4 border-b border-slate-700 pb-2">
              Business Overview
            </h2>
            
            <div className="space-y-8">
              <div>
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">What does this company do?</h3>
                <p className="text-slate-200 text-base leading-relaxed mb-4">
                  {intelligence?.business?.what_it_does || 'Not available.'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-8">
                <div>
                  <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Products</h3>
                  <div className="space-y-4">
                    {intelligence?.business?.products?.map((prodGroup: any, idx: number) => (
                      <div key={idx}>
                        <div className="text-slate-300 font-medium text-sm mb-1">{prodGroup.category}</div>
                        <ul className="text-slate-400 pl-4 border-l border-slate-700 text-sm space-y-1">
                          {prodGroup.items.map((item: string, i: number) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                    {!intelligence?.business?.products?.length && (
                      <div className="text-slate-500 text-sm italic">Not enough evidence yet.</div>
                    )}
                  </div>
                </div>

                <div className="space-y-8">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Manufacturing</h3>
                    <div className="space-y-3 text-sm">
                      {intelligence?.business?.manufacturing?.map((mfg: any, idx: number) => (
                        <div key={idx}>
                          <div className="text-slate-200 font-medium mb-1">
                            {mfg.location}
                          </div>
                          <div className="pl-4 text-slate-400">
                            {mfg.description}
                          </div>
                        </div>
                      ))}
                      {!intelligence?.business?.manufacturing?.length && (
                        <div className="text-slate-500 text-sm italic">Not enough evidence yet.</div>
                      )}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Revenue Mix</h3>
                    <div className="space-y-3 font-mono text-xs">
                      {intelligence?.business?.revenue_mix?.map((rev: any, idx: number) => (
                        <div key={idx}>
                          <div className="flex justify-between text-slate-400 mb-1">
                            <span>{rev.segment}</span>
                            <span>{rev.percentage_str}</span>
                          </div>
                          <div className="h-2 bg-slate-800 rounded overflow-hidden flex">
                            <div className="bg-emerald-500 w-[100%]"></div>
                          </div>
                        </div>
                      ))}
                      {!intelligence?.business?.revenue_mix?.length && (
                        <div className="text-slate-500 text-sm italic">Not enough evidence yet.</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'growth' && hasKnowledge && (
          <section className="mb-8 bg-slate-800/50 rounded-lg p-6 border border-slate-700 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <h2 className="text-xl font-bold text-slate-100 mb-4 border-b border-slate-700 pb-2">
              Growth Drivers
            </h2>
            <div className="space-y-8">
              {intelligence?.growth?.drivers?.map((driver: any, idx: number) => (
                <div key={idx} className="border-b border-slate-700/50 pb-6 last:border-0 last:pb-0">
                  <h3 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <span className="text-slate-500">{idx + 1}.</span> {driver.category}
                  </h3>
                  <div className="pl-6 space-y-4">
                    <p className="text-slate-200 text-sm font-medium">{driver.fact}</p>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Why it matters</h4>
                      <p className="text-slate-400 text-sm">{driver.why_it_matters}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Evidence</h4>
                      <EvidenceQuote quote={driver.evidence_quote} source={`${driver.evidence_source}${driver.evidence_date ? ` (${driver.evidence_date})` : ''}`} />
                    </div>
                  </div>
                </div>
              ))}
              {!intelligence?.growth?.drivers?.length && (
                <div className="text-slate-500 text-sm italic">Not enough evidence yet.</div>
              )}
            </div>
          </section>
        )}

        {['overview', 'management', 'decision', 'financials', 'technical', 'documents', 'risks'].includes(activeTab) && (
          <section className="mb-8 bg-slate-800/50 rounded-lg p-6 border border-slate-700 text-center py-12">
            <div className="text-slate-400 italic">This section is not compiled yet.</div>
          </section>
        )}

      </div>
    </div>
  );
};
