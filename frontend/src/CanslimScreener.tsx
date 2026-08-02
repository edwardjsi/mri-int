import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface CanslimCandidate {
    symbol: string;
    canslim_score: number;
    knowledge_age_days: number | null;
    compiler_version: string | null;
    components: {
        Growth: ComponentData;
        Quality: ComponentData;
        Momentum: ComponentData;
        Leadership: ComponentData;
        Market: ComponentData;
        Catalyst: ComponentData;
        Institutional: ComponentData;
    };
}

interface ComponentData {
    status: 'PASS' | 'FAIL' | 'UNKNOWN' | 'STALE' | 'ENRICHING' | 'NOT_APPLICABLE';
    observations: string[];
    rules: string[];
    evidence: string[];
    extraction_version?: string;
}

export const CanslimScreener: React.FC = () => {
    const [candidates, setCandidates] = useState<CanslimCandidate[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();

    const fetchScreen = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/v1/canslim/screen');
            if (!res.ok) throw new Error('Failed to fetch CANSLIM screener data');
            const data = await res.json();
            setCandidates(data.candidates);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchScreen();
    }, []);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'PASS': return '#10b981';
            case 'FAIL': return '#ef4444';
            case 'STALE': return '#f59e0b';
            case 'ENRICHING': return '#3b82f6';
            case 'NOT_APPLICABLE': return '#6b7280';
            case 'UNKNOWN':
            default: return '#9ca3af';
        }
    };

    const renderTooltipContent = (comp: ComponentData) => {
        if (!comp.evidence || comp.evidence.length === 0) return 'No evidence.';
        return (
            <div style={{ textAlign: 'left', minWidth: '200px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Rules Executed:</div>
                <div style={{ fontSize: '11px', marginBottom: '8px', color: '#93c5fd' }}>{comp.rules?.join(', ')}</div>
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Observations:</div>
                <div style={{ fontSize: '11px', marginBottom: '8px', color: '#fca5a5' }}>{comp.observations?.join(', ') || 'None'}</div>
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Evidence:</div>
                <div style={{ fontSize: '11px', fontStyle: 'italic' }}>"{comp.evidence.join(' ')}"</div>
            </div>
        );
    };

    const renderStatusCell = (comp: ComponentData, letter: string) => {
        const color = getStatusColor(comp.status);
        return (
            <div className="tooltip-container" style={{ display: 'inline-block' }}>
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    backgroundColor: `${color}20`,
                    border: `1px solid ${color}`,
                    color: color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 'bold',
                    fontSize: '14px',
                    cursor: 'help'
                }}>
                    {letter}
                </div>
                {comp.status === 'PASS' && (
                    <div className="tooltip-content" style={{ zIndex: 100 }}>
                        {renderTooltipContent(comp)}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', color: 'var(--text-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '32px' }}>
                <div>
                    <h1 style={{ margin: '0 0 8px 0', fontSize: '28px' }}>CANSLIM Discovery Funnel</h1>
                    <p style={{ margin: 0, color: 'var(--text-muted)' }}>Top quantitative candidates evaluated across the CANSLIM model framework.</p>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                    <button className="btn" onClick={fetchScreen}>Refresh Quant Screen</button>
                    <button className="btn btn-primary" disabled>Refresh Stale Knowledge (Sprint 2)</button>
                </div>
            </div>

            {loading && <p>Loading CANSLIM Candidates...</p>}
            {error && <div style={{ color: 'red', padding: '16px', border: '1px solid red', borderRadius: '8px' }}>Error: {error}</div>}

            {!loading && !error && (
                <div className="card" style={{ overflow: 'visible' }}>
                    <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center' }}>
                        <thead>
                            <tr>
                                <th style={{ textAlign: 'left', padding: '16px' }}>Symbol</th>
                                <th>Score</th>
                                <th>C<br/><span style={{fontSize: '10px', color: 'var(--text-muted)'}}>(Growth)</span></th>
                                <th>A<br/><span style={{fontSize: '10px', color: 'var(--text-muted)'}}>(Quality)</span></th>
                                <th>N<br/><span style={{fontSize: '10px', color: 'var(--text-muted)'}}>(Catalyst)</span></th>
                                <th>S<br/><span style={{fontSize: '10px', color: 'var(--text-muted)'}}>(Momentum)</span></th>
                                <th>L<br/><span style={{fontSize: '10px', color: 'var(--text-muted)'}}>(Leadership)</span></th>
                                <th>I<br/><span style={{fontSize: '10px', color: 'var(--text-muted)'}}>(Instit.)</span></th>
                                <th>M<br/><span style={{fontSize: '10px', color: 'var(--text-muted)'}}>(Market)</span></th>
                                <th>Knowledge<br/>Freshness</th>
                            </tr>
                        </thead>
                        <tbody>
                            {candidates.map(c => (
                                <tr key={c.symbol} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                    <td style={{ textAlign: 'left', padding: '16px' }}>
                                        <div 
                                            style={{ fontWeight: 'bold', fontSize: '18px', color: '#60a5fa', cursor: 'pointer' }}
                                            onClick={() => navigate(`/company/${c.symbol}`)}
                                        >
                                            {c.symbol}
                                        </div>
                                    </td>
                                    <td>
                                        <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{c.canslim_score}</div>
                                    </td>
                                    <td>{renderStatusCell(c.components.Growth, 'C')}</td>
                                    <td>{renderStatusCell(c.components.Quality, 'A')}</td>
                                    <td>{renderStatusCell(c.components.Catalyst, 'N')}</td>
                                    <td>{renderStatusCell(c.components.Momentum, 'S')}</td>
                                    <td>{renderStatusCell(c.components.Leadership, 'L')}</td>
                                    <td>{renderStatusCell(c.components.Institutional, 'I')}</td>
                                    <td>{renderStatusCell(c.components.Market, 'M')}</td>
                                    <td>
                                        {c.knowledge_age_days !== null ? `${c.knowledge_age_days} days` : <span style={{ color: 'var(--text-muted)' }}>No Knowledge</span>}
                                    </td>
                                </tr>
                            ))}
                            {candidates.length === 0 && (
                                <tr>
                                    <td colSpan={10} style={{ padding: '32px', color: 'var(--text-muted)' }}>
                                        No candidates met the minimum CANSLIM Quant filters.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};
