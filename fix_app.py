import re

with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

nav_links = """        <div className="nav-links">
          <Link to="/dashboard" className={`nav-link ${page === 'dashboard' ? 'active' : ''}`}><span className="nav-icon">📊</span> Dashboard</Link>
          <Link to="/inbox" className={`nav-link ${page === 'inbox' ? 'active' : ''}`}><span className="nav-icon">📥</span> Research Inbox</Link>
          <Link to="/extractor" className={`nav-link ${page === 'extractor' ? 'active' : ''}`}><span className="nav-icon">🧠</span> Ontology Engine</Link>
          <Link to="/ledger" className={`nav-link ${page === 'ledger' ? 'active' : ''}`}><span className="nav-icon">📋</span> Decision Ledger</Link>
          
          {/* Restored links */}
          <Link to="/signals" className={`nav-link ${page === 'signals' ? 'active' : ''}`}><span className="nav-icon">📈</span> Signal Dashboard</Link>
          <Link to="/caidashboard" className={`nav-link ${page === 'caidashboard' ? 'active' : ''}`}><span className="nav-icon">🧠</span> CAI Dashboard</Link>
          <Link to="/caiportfolio" className={`nav-link ${page === 'caiportfolio' ? 'active' : ''}`}><span className="nav-icon">💼</span> CAI Portfolio</Link>
          <Link to="/shadow" className={`nav-link ${page === 'shadow' ? 'active' : ''}`}><span className="nav-icon">🔄</span> Swing Momentum</Link>
          <Link to="/breakout" className={`nav-link ${page === 'breakout' ? 'active' : ''}`}><span className="nav-icon">🚀</span> Breakout Radar</Link>
          <Link to="/trend" className={`nav-link ${page === 'trend' ? 'active' : ''}`}><span className="nav-icon">📉</span> Trend Screen</Link>
          <Link to="/112co" className={`nav-link ${page === '112co' ? 'active' : ''}`}><span className="nav-icon">🦅</span> 112Co</Link>
          <Link to="/watchlist" className={`nav-link ${page === 'watchlist' ? 'active' : ''}`}><span className="nav-icon">👀</span> Watchlist</Link>
          <Link to="/perx" className={`nav-link ${page === 'perx' ? 'active' : ''}`}><span className="nav-icon">🏛️</span> PERX</Link>
          <Link to="/peexpansion" className={`nav-link ${page === 'peexpansion' ? 'active' : ''}`}><span className="nav-icon">🔍</span> Expansion Lens</Link>
          <Link to="/aae" className={`nav-link ${page === 'aae' ? 'active' : ''}`}><span className="nav-icon">🧬</span> AAE Console</Link>
          <Link to="/unified" className={`nav-link ${page === 'unified' ? 'active' : ''}`}><span className="nav-icon">🎯</span> Unified Scan</Link>
          <Link to="/guidance" className={`nav-link ${page === 'guidance' ? 'active' : ''}`}><span className="nav-icon">🗣️</span> GuidanceCheck</Link>
          <Link to="/conviction" className={`nav-link ${page === 'conviction' ? 'active' : ''}`}><span className="nav-icon">🔥</span> Conviction</Link>
          <Link to="/riskaudit" className={`nav-link ${page === 'riskaudit' ? 'active' : ''}`}><span className="nav-icon">🛡️</span> Risk Audit</Link>
          
          {isAdmin() && (
            <Link to="/admin" className={`nav-link ${page === 'admin' ? 'active' : ''}`}>
              <span className="nav-icon">🛡️</span> Platform Intel
            </Link>
          )}
        </div>"""

routes_str = """              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<V1Dashboard />} />
              <Route path="/decision/:decisionId" element={<StockDecisionPage />} />
              <Route path="/ledger" element={<HistoryPage onSelectStock={() => {}} />} />
              <Route path="/company/:symbol" element={<CiwDebuggerPage />} />
              <Route path="/inbox" element={<ResearchInbox />} />
              <Route path="/extractor" element={<AkeDashboard />} />
              
              {/* Restored routes */}
              <Route path="/signals" element={<DashboardPage onSelectStock={() => {}} />} />
              <Route path="/caidashboard" element={<CaiDashboard onNavigate={() => {}} />} />
              <Route path="/caiportfolio" element={<CaiPortfolioPage />} />
              <Route path="/shadow" element={<ShadowMomentumPage onSelectStock={() => {}} />} />
              <Route path="/riskaudit" element={<RiskAuditPage onSelectStock={() => {}} />} />
              <Route path="/watchlist" element={<WatchlistPage onSelectStock={() => {}} />} />
              <Route path="/112co" element={<One12CoDashboard onViewResearch={() => {}} />} />
              <Route path="/breakout" element={<BreakoutRadarPage onViewResearch={() => {}} />} />
              <Route path="/trend" element={<TrendScreen onViewResearch={() => {}} />} />
              <Route path="/perx" element={<PerxPage />} />
              <Route path="/peexpansion" element={<PeExpansionReport symbol="" onBack={() => {}} />} />
              <Route path="/aae" element={<AaeDashboard onBack={() => {}} onNavigate={() => {}} />} />
              <Route path="/unified" element={<UnifiedAnalysis onBack={() => {}} />} />
              <Route path="/guidance" element={<GuidanceCheck />} />
              <Route path="/conviction" element={<ConvictionEngine onSelectStock={() => {}} />} />
              <Route path="/admin" element={<AdminDashboard onSelectStock={() => {}} />} />
              <Route path="/research" element={<ResearchReport symbol="" onBack={() => {}} />} />
              
              <Route path="*" element={<Navigate to="/dashboard" replace />} />"""

content = re.sub(r'<div className="nav-links">.*?</div>', nav_links, content, flags=re.DOTALL)
content = re.sub(r'<Route path="/" element={<Navigate to="/dashboard" replace />} />.*?</Routes>', routes_str + '\n            </Routes>', content, flags=re.DOTALL)

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)

print("Done patching App.tsx")
