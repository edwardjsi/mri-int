import { useState } from 'react';
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

  if (symbol !== 'GRANULES') {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-200 p-8 font-sans">
        <div className="max-w-4xl mx-auto">
          <header className="mb-6 border-b border-slate-700 pb-4 flex justify-between items-end">
            <div>
              <h1 className="text-sm text-slate-400 uppercase tracking-widest">Investment Dossier v0.4</h1>
            </div>
          </header>
          
          <section className="bg-slate-900 border border-slate-700 rounded-lg p-6 shadow-2xl">
            <h2 className="text-2xl font-bold text-white tracking-tight mb-6 pb-4 border-b border-slate-800">{symbol}</h2>
            
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Knowledge Status</h3>
              <div className="flex items-center gap-2 text-rose-400 font-medium">
                <span>⚠</span> Investment dossier not available yet.
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-8 mb-8">
              <div>
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Available</h3>
                <ul className="space-y-2 text-slate-300">
                  <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Price history</li>
                  <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Technical indicators</li>
                  <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Financial statements</li>
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Missing</h3>
                <ul className="space-y-2 text-slate-400">
                  <li>• Business</li>
                  <li>• Growth</li>
                  <li>• Risks</li>
                  <li>• Management</li>
                </ul>
              </div>
            </div>
            
            <div className="pt-6 border-t border-slate-800 flex justify-between items-center">
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Compile Status</div>
                <div className="text-slate-300 text-sm">Never compiled</div>
              </div>
              <button className="bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white font-bold py-2 px-4 rounded transition-colors">
                Compile MOSI
              </button>
            </div>
          </section>
        </div>
      </div>
    );
  }

  const mockModels = [
    { id: 'CANSLIM', status: 'PASS' },
    { id: 'RRG', status: 'LEADING' }
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <header className="mb-6 border-b border-slate-700 pb-4 flex justify-between items-end">
          <div>
            <h1 className="text-sm text-slate-400 uppercase tracking-widest">Investment Dossier v0.3</h1>
          </div>
        </header>

        {/* Sticky Investment Summary */}
        <section className="sticky top-4 z-10 mb-8 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-lg p-6 shadow-2xl">
          <div className="flex justify-between items-start mb-4 border-b border-slate-800 pb-4">
            <div>
                <h2 className="text-2xl font-bold text-white tracking-tight">{symbol}</h2>
                <div className="mt-3">
                    <ModelBadgeGroup models={mockModels} />
                </div>
            </div>
            <div className="flex flex-col items-end">
              <span className="text-xs text-slate-400 uppercase tracking-wider mb-1">Verified Knowledge</span>
              <div className="flex items-center gap-2">
                <div className="text-lg font-bold text-emerald-400">82%</div>
                <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className="w-[82%] h-full bg-emerald-500 rounded-full"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="mb-5 pb-5 border-b border-slate-800">
            <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2">Can I explain this company in 30 seconds? <span className="text-emerald-400 ml-1">YES</span></div>
            <p className="text-slate-200 text-base leading-relaxed font-medium">
              Granules is transitioning from a commodity generic manufacturer toward higher-margin specialty pharmaceuticals through capacity expansion and US product launches.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-2">Investment Thesis</div>
                <ul className="text-slate-200 text-sm leading-relaxed space-y-1">
                  <li>• Expanding into higher-margin oncology</li>
                  <li>• Strong US generic pipeline</li>
                  <li>• Operating leverage from new capacity</li>
                  <li>• Strong balance sheet</li>
                </ul>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Biggest catalyst</div>
                  <div className="text-emerald-400 text-sm font-medium mb-1">Block 4 expansion</div>
                  <div className="text-slate-400 text-xs">Expected contribution: <span className="text-slate-300">18% FY27 growth</span></div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Biggest risk</div>
                  <div className="text-rose-400 text-sm font-medium mb-1">US pricing pressure</div>
                  <div className="text-slate-400 text-xs">Potential impact: <span className="text-slate-300">↓ Gross Margin</span></div>
                  <div className="text-slate-400 text-xs mt-0.5 flex items-center gap-1">
                    Evidence: <span className="text-slate-300 bg-slate-800 px-1 rounded">3 sources</span>
                  </div>
                </div>
              </div>
              <div className="pt-2 border-t border-slate-800/50">
                <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Last major update</div>
                <div className="text-slate-300 text-sm">Raised FY27 guidance</div>
              </div>
            </div>
          </div>
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

        {activeTab === 'business' && (
          <section className="mb-8 bg-slate-800/50 rounded-lg p-6 border border-slate-700 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <h2 className="text-xl font-bold text-slate-100 mb-4 border-b border-slate-700 pb-2">
              Business Overview
            </h2>
            
            <div className="space-y-8">
              {/* Business Summary + Investment Snapshot */}
              <div>
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Summary</h3>
                <p className="text-slate-200 text-base leading-relaxed mb-4">
                  <strong>Granules is a pharmaceutical manufacturer specializing in a small number of high-volume generic medicines. It supplies ingredients as well as finished tablets to global pharmaceutical companies, with North America being its largest market.</strong>
                </p>
                
                <div className="bg-slate-800 border border-slate-700 rounded-md p-4 mb-4 text-sm">
                  <div className="text-slate-400 uppercase tracking-wider text-xs font-semibold mb-2">Core Competencies</div>
                  <div className="grid grid-cols-[160px_1fr] gap-y-2">
                    <div className="text-slate-400">Competitive Advantage</div><div className="text-slate-200">Large-scale, low-cost manufacturing</div>
                    <div className="text-slate-400">Largest Market</div><div className="text-slate-200">North America</div>
                    <div className="text-slate-400">Core Products</div><div className="text-slate-200">Paracetamol, Ibuprofen, Metformin</div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-8">
                {/* Products Hierarchy */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Products</h3>
                  <div className="space-y-4">
                    <div>
                      <div className="text-slate-300 font-medium text-sm mb-1">Pain Management</div>
                      <ul className="text-slate-400 pl-4 border-l border-slate-700 text-sm space-y-1">
                        <li>Paracetamol</li>
                        <li>Ibuprofen</li>
                      </ul>
                    </div>
                    <div>
                      <div className="text-slate-300 font-medium text-sm mb-1">Diabetes</div>
                      <ul className="text-slate-400 pl-4 border-l border-slate-700 text-sm space-y-1">
                        <li>Metformin</li>
                      </ul>
                    </div>
                    <div>
                      <div className="text-slate-300 font-medium text-sm mb-1">Muscle Relaxant</div>
                      <ul className="text-slate-400 pl-4 border-l border-slate-700 text-sm space-y-1">
                        <li>Methocarbamol</li>
                      </ul>
                    </div>
                    <div>
                      <div className="text-slate-300 font-medium text-sm mb-1">Respiratory</div>
                      <ul className="text-slate-400 pl-4 border-l border-slate-700 text-sm space-y-1">
                        <li>Guaifenesin</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="space-y-8">
                  {/* Manufacturing Footprint */}
                  <div>
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Manufacturing Footprint</h3>
                    
                    <div className="space-y-3 text-sm">
                      <div>
                        <div className="flex items-center gap-2 text-slate-200 font-medium mb-1">
                          <span className="text-lg">🇮🇳</span> India (7)
                        </div>
                        <div className="pl-7 text-slate-400 space-y-1">
                          <div>Vizag (Block 4 API, Oncology)</div>
                          <div>Gagillapur (World's largest single-site PFI facility)</div>
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center gap-2 text-slate-200 font-medium mb-1">
                          <span className="text-lg">🇺🇸</span> USA (1)
                        </div>
                        <div className="pl-7 text-slate-400">
                          <div>Virginia</div>
                        </div>
                      </div>
                    </div>
                    <div className="mt-2">
                      <EvidenceQuote quote="Block 4 at Unit-V, Vizag, focusing on Oncology APIs, was successfully commissioned." source="Q1 FY27 MOSI" />
                    </div>
                  </div>

                  {/* Geography */}
                  <div>
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Revenue Mix</h3>
                    <div className="space-y-3 font-mono text-xs">
                      <div>
                        <div className="flex justify-between text-slate-400 mb-1">
                          <span>North America</span>
                          <span>~55%</span>
                        </div>
                        <div className="h-2 bg-slate-800 rounded overflow-hidden flex">
                          <div className="bg-emerald-500 w-[55%]"></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-slate-400 mb-1">
                          <span>Europe</span>
                          <span>~17%</span>
                        </div>
                        <div className="h-2 bg-slate-800 rounded overflow-hidden flex">
                          <div className="bg-emerald-600 w-[17%]"></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-slate-400 mb-1">
                          <span>India / RoW</span>
                          <span>~28%</span>
                        </div>
                        <div className="h-2 bg-slate-800 rounded overflow-hidden flex">
                          <div className="bg-emerald-700 w-[28%]"></div>
                        </div>
                      </div>
                    </div>
                    <div className="mt-2">
                      <EvidenceQuote quote="Regulated markets (North America and Europe) account for ~72% of total revenues." source="FY24 Investor Presentation" />
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Customers</h3>
                <div className="flex items-center gap-2 text-slate-500 text-sm italic">
                  Not enough evidence yet.
                </div>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'growth' && (
          <section className="mb-8 bg-slate-800/50 rounded-lg p-6 border border-slate-700 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <h2 className="text-xl font-bold text-slate-100 mb-4 border-b border-slate-700 pb-2">
              Growth Drivers
            </h2>

            <div className="space-y-8">
              
              <div className="bg-slate-800/80 border border-emerald-900/50 rounded-lg p-5">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                    <span className="text-amber-400 tracking-widest text-xs">★★★★★</span> Capacity Expansion
                  </h3>
                  <div className="flex items-center gap-4">
                    <div className="text-xs text-slate-400 flex items-center gap-3 bg-slate-900/80 px-3 py-1 rounded-full border border-slate-700">
                      <span><strong className="text-slate-200">4</strong> documents</span>
                      <span className="w-1 h-1 bg-slate-600 rounded-full"></span>
                      <span><strong className="text-slate-200">9</strong> quotes</span>
                      <span className="w-1 h-1 bg-slate-600 rounded-full"></span>
                      <span>Updated <strong className="text-slate-200">3 days ago</strong></span>
                    </div>
                    <span className="text-xs font-semibold bg-emerald-900/50 text-emerald-400 px-2 py-1 rounded">HIGH IMPACT</span>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                  <div className="md:col-span-2">
                    <p className="text-slate-300 text-sm mb-3">
                      Significant new capacity is coming online across key manufacturing blocks to support volume growth.
                    </p>
                    <EvidenceQuote quote="Block 4 API facility commissioned in Q1 FY27, adding 35% to total oncology API capacity." source="Q1 FY27 Earnings Call" />
                  </div>
                  <div className="bg-slate-900/50 p-3 rounded text-sm">
                    <div className="text-slate-500 text-xs uppercase mb-1">Expected FY27 contribution</div>
                    <div className="text-slate-200 font-bold mb-3">18%</div>
                    
                    <div className="text-slate-500 text-xs uppercase mb-1">Confidence</div>
                    <div className="text-emerald-400 font-medium">High</div>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-start">
                <div className="max-w-2xl">
                  <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <span className="text-amber-400 tracking-widest text-xs">★★★★☆</span> US Launches
                  </h3>
                  <p className="text-slate-300 text-sm">
                    Accelerating ANDA approvals and new finished dosage launches in the high-margin North American market.
                  </p>
                  <EvidenceQuote quote="We have 14 new product launches planned for the US market over the next 12 months." source="FY24 Investor Presentation" />
                </div>
                <div className="text-xs text-slate-400 flex flex-col items-end gap-1 bg-slate-800/30 px-3 py-2 rounded border border-slate-700/50">
                  <span><strong className="text-slate-200">2</strong> documents</span>
                  <span><strong className="text-slate-200">5</strong> quotes</span>
                </div>
              </div>
              
              <div className="flex justify-between items-start">
                <div className="max-w-2xl">
                  <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <span className="text-amber-400 tracking-widest text-xs">★★★★☆</span> Oncology
                  </h3>
                  <p className="text-slate-300 text-sm">
                    Expansion into higher value segments including Oncology and complex formulations to drive realization.
                  </p>
                  <EvidenceQuote quote="Our entry into oncology and MUPS formulations will improve our overall gross margin profile." source="Q1 FY27 Earnings Call" />
                </div>
                <div className="text-xs text-slate-400 flex flex-col items-end gap-1 bg-slate-800/30 px-3 py-2 rounded border border-slate-700/50">
                  <span><strong className="text-slate-200">1</strong> document</span>
                  <span><strong className="text-slate-200">3</strong> quotes</span>
                </div>
              </div>

              <div className="flex justify-between items-start">
                <div className="max-w-2xl">
                  <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <span className="text-amber-400 tracking-widest text-xs">★★★☆☆</span> Volume
                  </h3>
                  <p className="text-slate-300 text-sm">
                    Ramping up production at recently expanded facilities to drive operating leverage and raw volume growth.
                  </p>
                  <EvidenceQuote quote="Capacity utilization at Gagillapur is expected to improve from 68% to 85% by end of FY27." source="Q1 FY27 Management Commentary" />
                </div>
                <div className="text-xs text-slate-400 flex flex-col items-end gap-1 bg-slate-800/30 px-3 py-2 rounded border border-slate-700/50">
                  <span><strong className="text-slate-200">3</strong> documents</span>
                  <span><strong className="text-slate-200">4</strong> quotes</span>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-700/50">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                  <span className="text-amber-400 tracking-widest text-xs">★★☆☆☆</span> Pricing
                </h3>
                <div className="flex items-center gap-2 text-slate-500 text-sm italic">
                  Not enough evidence yet.
                </div>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'risks' && (
          <section className="mb-8 bg-slate-800/50 rounded-lg p-6 border border-slate-700 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <h2 className="text-xl font-bold text-slate-100 mb-4 border-b border-slate-700 pb-2">
              Key Risks
            </h2>

            <div className="space-y-6">
              <div className="bg-slate-800/80 border border-rose-900/50 rounded-lg p-5">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-sm font-semibold text-rose-400 uppercase tracking-wider flex items-center gap-2">
                    <span className="text-amber-400 tracking-widest text-xs">★★★★★</span> US Pricing Pressure
                  </h3>
                  <div className="flex items-center gap-4">
                    <div className="text-xs text-slate-400 flex items-center gap-3 bg-slate-900/80 px-3 py-1 rounded-full border border-slate-700">
                      <span><strong className="text-slate-200">3</strong> documents</span>
                      <span className="w-1 h-1 bg-slate-600 rounded-full"></span>
                      <span><strong className="text-slate-200">6</strong> quotes</span>
                    </div>
                    <span className="text-xs font-semibold bg-rose-900/50 text-rose-400 px-2 py-1 rounded">HIGH IMPACT</span>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                  <div className="md:col-span-2">
                    <p className="text-slate-300 text-sm mb-3">
                      High competition in the US generics market continues to drive price erosion, threatening gross margins.
                    </p>
                    <EvidenceQuote quote="We experienced mid-single-digit price erosion in our base US portfolio during the quarter." source="Q1 FY27 Earnings Call" />
                  </div>
                  <div className="bg-slate-900/50 p-3 rounded text-sm">
                    <div className="text-slate-500 text-xs uppercase mb-1">Potential Impact</div>
                    <div className="text-rose-400 font-bold mb-3">↓ Gross Margin</div>
                    
                    <div className="text-slate-500 text-xs uppercase mb-1">Probability</div>
                    <div className="text-rose-400 font-medium">High</div>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-start">
                <div className="max-w-2xl">
                  <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <span className="text-amber-400 tracking-widest text-xs">★★★☆☆</span> Regulatory Compliance
                  </h3>
                  <p className="text-slate-300 text-sm">
                    Exposure to FDA inspections and potential warning letters at key manufacturing facilities like Gagillapur.
                  </p>
                  <EvidenceQuote quote="The Gagillapur facility underwent an FDA inspection resulting in 3 minor observations which have been addressed." source="FY24 Annual Report" />
                </div>
                <div className="text-xs text-slate-400 flex flex-col items-end gap-1 bg-slate-800/30 px-3 py-2 rounded border border-slate-700/50">
                  <span><strong className="text-slate-200">2</strong> documents</span>
                  <span><strong className="text-slate-200">2</strong> quotes</span>
                </div>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'technical' && (
          <section className="mb-8 bg-slate-800/50 rounded-lg p-6 border border-slate-700 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <h2 className="text-xl font-bold text-slate-100 mb-4 border-b border-slate-700 pb-2">
              Technical Details
            </h2>

            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                  Manufacturing Value Chain
                </h3>
                <p className="text-slate-300 mb-2">
                  Granules operates as a vertically integrated pharmaceutical manufacturer across three primary stages of the value chain:
                </p>
                <ul className="list-disc list-inside text-slate-300 space-y-1 mb-4 pl-2">
                  <li><strong>Active Pharmaceutical Ingredients (APIs):</strong> The biologically active components in a pharmaceutical drug.</li>
                  <li><strong>Pharmaceutical Formulation Intermediates (PFIs):</strong> The stage between APIs and finished dosages, optimizing the manufacturing process.</li>
                  <li><strong>Finished Dosages (FDs):</strong> The final consumable products, primarily in tablet form.</li>
                </ul>
                <EvidenceQuote quote="We are a vertically integrated pharmaceutical company manufacturing Active Pharmaceutical Ingredients (APIs), Pharmaceutical Formulation Intermediates (PFIs) and Finished Dosages (FDs)." source="FY24 Annual Report" />
              </div>
            </div>
          </section>
        )}

        {['overview', 'management', 'decision', 'financials', 'documents'].includes(activeTab) && (
          <section className="mb-8 bg-slate-800/50 rounded-lg p-6 border border-slate-700 text-center py-12">
            <div className="text-slate-400 italic">This section is not compiled yet.</div>
          </section>
        )}

        {/* Knowledge Sources Footer */}
        <footer className="mt-12 mb-8 bg-slate-900 border border-slate-700 rounded-lg p-6 shadow-xl">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Knowledge Sources</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <ul className="space-y-2 text-slate-300 text-sm">
              <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Annual Report FY25</li>
              <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Q1 FY26 Transcript</li>
            </ul>
            <ul className="space-y-2 text-slate-300 text-sm">
              <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Investor Presentation</li>
              <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Shareholding Pattern</li>
            </ul>
          </div>
          <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Last compiled</div>
              <div className="text-slate-300 text-sm">2 Aug 2026</div>
            </div>
            <button className="text-xs text-emerald-400 border border-emerald-400/50 hover:bg-emerald-400/10 px-3 py-1.5 rounded transition-colors">
              View Source Graph
            </button>
          </div>
        </footer>

      </div>
    </div>
  );
};

export default CompanyDossier;

