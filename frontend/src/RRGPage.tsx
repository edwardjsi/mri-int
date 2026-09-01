import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from './api';
import { RrgScatterPlot } from './RrgScatterPlot';

const DEFAULT_COLUMNS = {
  select: true,
  rank: true,
  owned: true,
  symbol: true,
  company: true,
  quadrant: true,
  rs_ratio: true,
  rs_momentum: true,
  heading: true,
};

export const RRGPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [data, setData] = useState<any[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>('Never');
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedSymbols, setSelectedSymbols] = useState<Set<string>>(new Set());

  // Extract from URL or defaults
  const quadrantFilter = searchParams.get('quadrant') || 'All';
  const sortKey = searchParams.get('sort') || 'rs_ratio';
  const sortOrder = searchParams.get('order') || 'desc';
  const searchQuery = searchParams.get('search') || '';
  const universeFilter = searchParams.get('universe') || 'All';

  // Column chooser state (localStorage)
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem('rrg.columns');
      if (saved) {
        const parsed = JSON.parse(saved);
        // Ensure new columns like 'select' are visible even if older state is cached
        return { ...DEFAULT_COLUMNS, ...parsed, select: parsed.select ?? DEFAULT_COLUMNS.select };
      }
      return DEFAULT_COLUMNS;
    } catch {
      return DEFAULT_COLUMNS;
    }
  });
  
  const [showColumnChooser, setShowColumnChooser] = useState(false);

  useEffect(() => {
    localStorage.setItem('rrg.columns', JSON.stringify(visibleColumns));
  }, [visibleColumns]);

  const toggleColumn = (col: string) => {
    setVisibleColumns(prev => ({ ...prev, [col]: !prev[col] }));
  };

  useEffect(() => {
    setLoading(true);
    api.getRRG(sortKey, sortOrder, quadrantFilter, universeFilter)
      .then((res: any) => {
        if (res && res.results) {
          setData(res.results);
          if (res.last_updated) {
             setLastUpdated(new Date(res.last_updated).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }));
          }
          setTotalCount(res.total_count || 0);
        } else if (res.error) {
          setError(res.error);
        } else {
          setData([]);
        }
      })
      .catch((err: any) => setError(err.message))
      .finally(() => setLoading(false));
  }, [sortKey, sortOrder, quadrantFilter, universeFilter]);

  const handleSort = (key: string) => {
    const newOrder = (sortKey === key && sortOrder === 'desc') ? 'asc' : 'desc';
    setSearchParams(prev => {
      prev.set('sort', key);
      prev.set('order', newOrder);
      return prev;
    });
  };

  const setQuadrantFilter = (q: string) => {
    setSearchParams(prev => {
      if (q === 'All') prev.delete('quadrant');
      else prev.set('quadrant', q);
      return prev;
    });
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setSearchParams(prev => {
      if (!val) prev.delete('search');
      else prev.set('search', val);
      return prev;
    });
  };

  const getSortIcon = (key: string) => {
    if (sortKey !== key) return '↑↓';
    return sortOrder === 'asc' ? '↑' : '↓';
  };

  // Client-side text search filter
  const filteredData = useMemo(() => {
    if (!searchQuery) return data;
    const query = searchQuery.toLowerCase();
    return data.filter(item => 
      (item.symbol?.toLowerCase().includes(query) || item.company_name?.toLowerCase().includes(query))
    );
  }, [data, searchQuery]);

  // Compute Rank dynamically
  const rankedData = useMemo(() => {
    return filteredData.map((item, idx) => ({
      ...item,
      computed_rank: idx + 1
    }));
  }, [filteredData]);

  // Top 20 per quadrant for Scatter Plot (or selected symbols if any)
  const scatterPlotData = useMemo(() => {
    if (selectedSymbols.size > 0) {
      return data.filter(item => selectedSymbols.has(item.symbol));
    }
    
    const groups: Record<string, any[]> = {};
    
    filteredData.forEach(item => {
      const q = item.rrg?.quadrant?.toUpperCase() || 'UNKNOWN';
      if (!groups[q]) groups[q] = [];
      groups[q].push(item);
    });

    const result: any[] = [];
    Object.values(groups).forEach(group => {
      const sorted = [...group].sort((a, b) => {
        const distA = Math.pow((a.rrg?.rs_ratio || 100) - 100, 2) + Math.pow((a.rrg?.rs_momentum || 100) - 100, 2);
        const distB = Math.pow((b.rrg?.rs_ratio || 100) - 100, 2) + Math.pow((b.rrg?.rs_momentum || 100) - 100, 2);
        return distB - distA; // descending
      });
      result.push(...sorted.slice(0, 20));
    });

    return result;
  }, [filteredData, data, selectedSymbols]);

  // Summary strip counts
  const counts = useMemo(() => {
    const c = { LEADING: 0, IMPROVING: 0, WEAKENING: 0, LAGGING: 0 };
    // Compute total counts based on full data array before client search filter, but affected by server quadrant filter
    data.forEach(item => {
      const q = item.rrg?.quadrant?.toUpperCase();
      if (q && q in c) c[q as keyof typeof c]++;
    });
    return c;
  }, [data]);

  const getQuadrantBadge = (quadrant: string) => {
    switch (quadrant?.toUpperCase()) {
      case 'LEADING': return <span className="bg-emerald-900/50 text-emerald-400 px-2 py-1 rounded text-xs font-semibold">🟢 LEADING</span>;
      case 'IMPROVING': return <span className="bg-amber-900/50 text-amber-400 px-2 py-1 rounded text-xs font-semibold">🟡 IMPROVING</span>;
      case 'WEAKENING': return <span className="bg-orange-900/50 text-orange-400 px-2 py-1 rounded text-xs font-semibold">🟠 WEAKENING</span>;
      case 'LAGGING': return <span className="bg-rose-900/50 text-rose-400 px-2 py-1 rounded text-xs font-semibold">🔴 LAGGING</span>;
      default: return <span className="bg-slate-800 text-slate-400 px-2 py-1 rounded text-xs">{quadrant || 'UNKNOWN'}</span>;
    }
  };

  if (loading && data.length === 0) return <div className="p-8 text-slate-300">Loading Relative Rotation Data...</div>;
  if (error) return <div className="p-8 text-rose-400">Error loading data: {error}</div>;

  return (
    <div className="p-8 font-sans bg-slate-900 min-h-screen text-slate-200">
      <div className="max-w-7xl mx-auto">
        
        {/* Header matching requested style */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 pb-4 border-b border-slate-800 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Relative Rotation</h1>
            <div className="flex gap-6 text-sm">
              <div>
                 <span className="text-slate-500 mr-2">Showing</span>
                 <span className="text-slate-300 font-medium">{filteredData.length} / {totalCount}</span>
              </div>
              <div>
                 <span className="text-slate-500 mr-2">Updated</span>
                 <span className="text-slate-300 font-medium">{lastUpdated}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4 w-full md:w-auto relative">
            <div className="relative w-full md:w-64">
              <input 
                type="text" 
                placeholder="Search..."
                value={searchQuery}
                onChange={handleSearch}
                className="bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 w-full focus:outline-none focus:border-emerald-500"
              />
              <span className="absolute left-3 top-2.5 text-slate-500 text-sm">🔍</span>
            </div>
            
            <button 
              onClick={() => setShowColumnChooser(!showColumnChooser)}
              className="bg-slate-800 border border-slate-700 text-slate-300 px-4 py-2 rounded-lg text-sm hover:bg-slate-700 transition-colors whitespace-nowrap"
            >
              ⚙️ Columns
            </button>
            
            {showColumnChooser && (
              <div className="absolute top-12 right-0 bg-slate-800 border border-slate-700 rounded-lg shadow-xl p-4 z-10 w-48 flex flex-col gap-2">
                <h4 className="text-xs text-slate-400 uppercase mb-2 font-semibold tracking-wider">Show/Hide</h4>
                {Object.keys(visibleColumns).map(col => (
                  <label key={col} className="flex items-center gap-2 text-sm cursor-pointer hover:text-white">
                    <input 
                      type="checkbox" 
                      checked={visibleColumns[col]} 
                      onChange={() => toggleColumn(col)} 
                      className="accent-emerald-500"
                    />
                    <span className="capitalize">{col.replace('_', ' ')}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </header>

        {/* Summary Strip & Controls */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
          <div className="flex flex-wrap gap-2">
            <span className="text-slate-400 self-center text-sm mr-2 font-medium">Universe:</span>
            {['All', '112co'].map(u => (
              <button
                key={u}
                onClick={() => setSearchParams(prev => { if (u === 'All') prev.delete('universe'); else prev.set('universe', u); return prev; })}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors border ${universeFilter === u ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-900/50' : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:text-slate-200'}`}
              >
                {u}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <span className="text-slate-400 self-center text-sm mr-2 font-medium">Quadrant:</span>
            {['All', 'LEADING', 'IMPROVING', 'WEAKENING', 'LAGGING'].map(q => (
              <button
                key={q}
                onClick={() => setQuadrantFilter(q)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors border ${quadrantFilter === q ? 'bg-slate-700 border-slate-500 text-white shadow-lg shadow-slate-900/50' : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:text-slate-200'}`}
              >
                {q === 'All' ? q : q.charAt(0) + q.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
          
          {quadrantFilter === 'All' && (
            <div className="flex gap-6 text-sm font-medium">
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500"></span><span className="text-slate-400">Leading</span><span className="text-white">{counts.LEADING}</span></div>
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-amber-500"></span><span className="text-slate-400">Improving</span><span className="text-white">{counts.IMPROVING}</span></div>
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-orange-500"></span><span className="text-slate-400">Weakening</span><span className="text-white">{counts.WEAKENING}</span></div>
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-rose-500"></span><span className="text-slate-400">Lagging</span><span className="text-white">{counts.LAGGING}</span></div>
            </div>
          )}
        </div>

        {/* RRG Scatter Plot */}
        <RrgScatterPlot data={scatterPlotData} onDotClick={(symbol: string) => navigate(`/company/${symbol}`)} />

        {/* Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-800/50 text-slate-400 uppercase tracking-wider text-xs border-b border-slate-800">
                <tr>
                  {visibleColumns.select && <th className="px-4 py-4 w-12 text-center">Select</th>}
                  {visibleColumns.rank && <th className="px-6 py-4 font-medium text-center cursor-pointer hover:text-slate-200 w-16" onClick={() => handleSort('rank')}>Rank {getSortIcon('rank')}</th>}
                  {visibleColumns.owned && <th className="px-4 py-4 font-medium text-center cursor-pointer hover:text-slate-200 w-20" onClick={() => handleSort('owned')}>Owned {getSortIcon('owned')}</th>}
                  {visibleColumns.symbol && <th className="px-6 py-4 font-medium cursor-pointer hover:text-slate-200 w-32" onClick={() => handleSort('symbol')}>Symbol {getSortIcon('symbol')}</th>}
                  {visibleColumns.company && <th className="px-6 py-4 font-medium cursor-pointer hover:text-slate-200 min-w-[200px]" onClick={() => handleSort('company_name')}>Company Name {getSortIcon('company_name')}</th>}
                  {visibleColumns.quadrant && <th className="px-6 py-4 font-medium text-center cursor-pointer hover:text-slate-200" onClick={() => handleSort('quadrant')}>Quadrant {getSortIcon('quadrant')}</th>}
                  {visibleColumns.rs_ratio && <th className="px-6 py-4 font-medium text-right cursor-pointer hover:text-slate-200" onClick={() => handleSort('rs_ratio')}>RS Ratio {getSortIcon('rs_ratio')}</th>}
                  {visibleColumns.rs_momentum && <th className="px-6 py-4 font-medium text-right cursor-pointer hover:text-slate-200" onClick={() => handleSort('rs_momentum')}>RS Momentum {getSortIcon('rs_momentum')}</th>}
                  {visibleColumns.heading && <th className="px-6 py-4 font-medium text-right cursor-pointer hover:text-slate-200" onClick={() => handleSort('heading')}>Heading {getSortIcon('heading')}</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {rankedData.map((row) => (
                  <tr 
                    key={row.symbol} 
                    className={`hover:bg-slate-800/30 transition-colors cursor-pointer group ${selectedSymbols.has(row.symbol) ? 'bg-emerald-900/20' : ''}`}
                    onClick={() => navigate(`/company/${row.symbol}`)}
                  >
                    {visibleColumns.select && (
                      <td className="px-4 py-4 text-center" onClick={(e) => e.stopPropagation()}>
                        <input 
                          type="checkbox" 
                          className="accent-emerald-500 w-4 h-4 cursor-pointer"
                          checked={selectedSymbols.has(row.symbol)}
                          onChange={() => {
                            setSelectedSymbols(prev => {
                              const newSet = new Set(prev);
                              if (newSet.has(row.symbol)) {
                                newSet.delete(row.symbol);
                              } else {
                                if (newSet.size >= 10) {
                                  alert("You can select up to 10 stocks at a time to plot.");
                                  return prev;
                                }
                                newSet.add(row.symbol);
                              }
                              return newSet;
                            });
                          }}
                        />
                      </td>
                    )}
                    {visibleColumns.rank && <td className="px-6 py-4 text-slate-500 font-mono text-center">{row.computed_rank}</td>}
                    {visibleColumns.owned && (
                      <td className="px-4 py-4 text-center">
                        {row.owned ? <span className="text-emerald-400" title="In Portfolio">✓</span> : <span className="text-slate-600">-</span>}
                      </td>
                    )}
                    {visibleColumns.symbol && <td className="px-6 py-4 text-emerald-400 font-bold group-hover:text-emerald-300 w-32">{row.symbol}</td>}
                    {visibleColumns.company && <td className="px-6 py-4 text-slate-300 min-w-[200px] truncate">{row.company_name}</td>}
                    {visibleColumns.quadrant && <td className="px-6 py-4 text-center">{getQuadrantBadge(row.rrg?.quadrant)}</td>}
                    {visibleColumns.rs_ratio && <td className="px-6 py-4 text-right font-mono text-slate-300">{Number(row.rrg?.rs_ratio).toFixed(2)}</td>}
                    {visibleColumns.rs_momentum && <td className="px-6 py-4 text-right font-mono text-slate-300">{Number(row.rrg?.rs_momentum).toFixed(2)}</td>}
                    {visibleColumns.heading && <td className="px-6 py-4 text-right font-mono text-slate-300">{Number(row.rrg?.heading).toFixed(2)}°</td>}
                  </tr>
                ))}
                
                {rankedData.length === 0 && !loading && (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center text-slate-500">
                      No companies found. Try removing one or more filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
};

export default RRGPage;
