import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiFetch } from './api';
import { ModelBadgeGroup } from './components/ModelBadge';

// --- Domain Models for CIW ---
export interface KnowledgeNode {
    id: string;
    node_type: string;
    text: string;
    confidence: string;
    status: string;
    evidence: any[];
    history: any[];
    updated_at: string;
    metadata: any;
}

export interface TimelineEvent {
    id: string;
    event_date: string;
    event_type: string;
    summary: string;
}

export interface KnowledgeHealth {
    overall: number;
    research_freshness: boolean;
    evidence_completeness: boolean;
    open_monitoring: number;
    open_risks: number;
    missing_evidence: number;
    last_update: string;
}

export interface CompanyWorkspace {
    identity: {
        symbol: string;
        name: string;
        sector: string;
    };
    portfolio: {
        status: string;
        allocation: number;
        average_cost: number;
    };
    state: {
        understanding: Record<string, KnowledgeNode>;
        risks: KnowledgeNode[];
        catalysts: KnowledgeNode[];
        monitoring: KnowledgeNode[];
    };
    timeline: TimelineEvent[];
    health: KnowledgeHealth;
    models?: any[];
}


// --- Components ---

const HealthPanel: React.FC<{ health: KnowledgeHealth }> = ({ health }) => {
    return (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-8 text-sm">
            <h3 className="text-gray-400 uppercase tracking-widest text-xs font-semibold mb-4">Knowledge Health</h3>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-center">
                <div>
                    <div className="text-2xl font-bold text-white">{health.overall}%</div>
                    <div className="text-gray-500 mt-1">Overall</div>
                </div>
                <div>
                    <div className="text-2xl font-bold text-white">{health.research_freshness ? '✔' : '✖'}</div>
                    <div className="text-gray-500 mt-1">Freshness</div>
                </div>
                <div>
                    <div className="text-2xl font-bold text-white">{health.evidence_completeness ? '✔' : '✖'}</div>
                    <div className="text-gray-500 mt-1">Evidence Complete</div>
                </div>
                <div>
                    <div className="text-2xl font-bold text-white">{health.open_monitoring}</div>
                    <div className="text-gray-500 mt-1">Open Monitoring</div>
                </div>
                <div>
                    <div className="text-2xl font-bold text-white">{health.open_risks}</div>
                    <div className="text-gray-500 mt-1">Open Risks</div>
                </div>
                <div>
                    <div className="text-2xl font-bold text-white">{health.missing_evidence}</div>
                    <div className="text-gray-500 mt-1">Missing Evidence</div>
                </div>
            </div>
            <div className="mt-4 text-gray-500 text-xs text-right">
                Last updated: {health.last_update !== 'Never' ? new Date(health.last_update).toLocaleDateString() : 'Never'}
            </div>
        </div>
    );
};

const NodeExpandable: React.FC<{ title: string, node: KnowledgeNode }> = ({ title, node }) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-4 hover:border-gray-700 transition-colors">
            <div className="flex justify-between items-start cursor-pointer" onClick={() => setExpanded(!expanded)}>
                <div>
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{title}</div>
                    <div className="text-lg text-gray-100 font-medium">{node.text}</div>
                </div>
                <button className="text-gray-500 hover:text-white">
                    {expanded ? '▲' : '▼'}
                </button>
            </div>
            
            {expanded && (
                <div className="mt-6 pt-4 border-t border-gray-800 space-y-4">
                    <div>
                        <h4 className="text-xs text-gray-400 uppercase tracking-widest mb-2">Evidence</h4>
                        {node.evidence && node.evidence.length > 0 ? (
                            <ul className="text-sm text-gray-300 list-disc pl-5">
                                {node.evidence.map((ev, i) => (
                                    <li key={i}>{typeof ev === 'string' ? ev : JSON.stringify(ev)}</li>
                                ))}
                            </ul>
                        ) : (
                            <div className="text-sm text-gray-600 italic">No formal evidence linked.</div>
                        )}
                    </div>
                    
                    <div>
                        <h4 className="text-xs text-gray-400 uppercase tracking-widest mb-2">Previous Version</h4>
                        {node.history && node.history.length > 0 ? (
                            <div className="text-sm text-gray-400 line-through">
                                {node.history[node.history.length - 1].text || JSON.stringify(node.history[0])}
                            </div>
                        ) : (
                            <div className="text-sm text-gray-600 italic">No previous versions.</div>
                        )}
                    </div>
                    
                    <div>
                        <h4 className="text-xs text-gray-400 uppercase tracking-widest mb-2">Changed By</h4>
                        <div className="text-sm font-mono text-gray-500">
                            Knowledge Update Transaction (Latest)
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export const CiwDebuggerPage: React.FC = () => {
    const { symbol } = useParams<{ symbol: string }>();
    const [workspace, setWorkspace] = useState<CompanyWorkspace | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchWorkspace = async () => {
            try {
                // Workaround for API fetch using standard fetch logic
                const res = await apiFetch(`ciw/${symbol}`);
                setWorkspace(res);
                setError(null);
            } catch (err: any) {
                setError(err.message || "Failed to load workspace.");
            } finally {
                setLoading(false);
            }
        };

        if (symbol) fetchWorkspace();
    }, [symbol]);

    if (loading) return <div className="p-8 text-gray-400">Loading CIW...</div>;
    if (error) return <div className="p-8 text-red-400">Error: {error}</div>;
    if (!workspace) return <div className="p-8 text-gray-400">No workspace data.</div>;

    const { thesis, business_quality } = workspace.state.understanding;

    return (
        <div className="min-h-screen bg-black text-gray-200 p-8 font-sans">
            <div className="max-w-4xl mx-auto">
                
                {/* 1. Header */}
                <header className="mb-10">
                    <Link to="/dashboard" className="text-indigo-400 hover:text-indigo-300 text-sm mb-4 inline-block">
                        &larr; Back to Dashboard
                    </Link>
                    <div className="flex items-end justify-between">
                        <div>
                            <h1 className="text-4xl font-bold text-white tracking-tight">{workspace.identity.symbol}</h1>
                            <h2 className="text-xl text-gray-400 mt-1">{workspace.identity.name}</h2>
                            <div className="mt-3">
                                {workspace.models && <ModelBadgeGroup models={workspace.models} />}
                            </div>
                        </div>
                        <div className="text-right">
                            <div className="text-sm text-gray-500 uppercase tracking-widest mb-1">Status</div>
                            <div className={`text-lg font-semibold ${workspace.portfolio.status === 'Owned' ? 'text-emerald-400' : 'text-gray-300'}`}>
                                {workspace.portfolio.status}
                            </div>
                        </div>
                    </div>
                </header>

                {/* 2. Knowledge Health */}
                {workspace.health && <HealthPanel health={workspace.health} />}

                {/* 3. Current Understanding */}
                <section className="mb-12">
                    <h3 className="text-gray-400 uppercase tracking-widest text-sm font-bold mb-6 border-b border-gray-800 pb-2">Current Understanding</h3>
                    {thesis && <NodeExpandable title="Core Thesis" node={thesis} />}
                    {business_quality && <NodeExpandable title="Business Quality" node={business_quality} />}
                </section>

                {/* 4. Why do we believe this? (Catalysts & Risks) */}
                <section className="mb-12">
                    <h3 className="text-gray-400 uppercase tracking-widest text-sm font-bold mb-6 border-b border-gray-800 pb-2">Why Do We Believe This?</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <h4 className="text-emerald-400 font-semibold mb-4 text-sm">CATALYSTS</h4>
                            {workspace.state.catalysts.map(c => (
                                <NodeExpandable key={c.id} title="Catalyst" node={c} />
                            ))}
                            {workspace.state.catalysts.length === 0 && <div className="text-gray-600 text-sm italic">No active catalysts.</div>}
                        </div>
                        <div>
                            <h4 className="text-red-400 font-semibold mb-4 text-sm">RISKS</h4>
                            {workspace.state.risks.map(r => (
                                <NodeExpandable key={r.id} title="Risk" node={r} />
                            ))}
                            {workspace.state.risks.length === 0 && <div className="text-gray-600 text-sm italic">No active risks.</div>}
                        </div>
                    </div>
                </section>

                {/* 5. Monitoring */}
                <section className="mb-12">
                    <h3 className="text-gray-400 uppercase tracking-widest text-sm font-bold mb-6 border-b border-gray-800 pb-2">Monitoring</h3>
                    {workspace.state.monitoring.map(m => (
                        <NodeExpandable key={m.id} title="Monitor" node={m} />
                    ))}
                    {workspace.state.monitoring.length === 0 && <div className="text-gray-600 text-sm italic">Nothing currently monitored.</div>}
                </section>

                {/* 6. Timeline */}
                <section className="mb-12">
                    <h3 className="text-gray-400 uppercase tracking-widest text-sm font-bold mb-6 border-b border-gray-800 pb-2">Timeline</h3>
                    <div className="space-y-6">
                        {workspace.timeline.map(event => (
                            <div key={event.id} className="flex">
                                <div className="w-32 text-gray-500 text-sm pt-1 shrink-0">
                                    {new Date(event.event_date).toLocaleDateString()}
                                </div>
                                <div className="pl-6 border-l border-gray-800 relative pb-4">
                                    <div className="absolute w-2 h-2 bg-indigo-500 rounded-full -left-[5px] top-2"></div>
                                    <div className="text-xs text-indigo-400 font-semibold uppercase tracking-wider mb-1">{event.event_type}</div>
                                    <div className="text-gray-300">{event.summary}</div>
                                </div>
                            </div>
                        ))}
                        {workspace.timeline.length === 0 && <div className="text-gray-600 text-sm italic">No events on timeline.</div>}
                    </div>
                </section>
                
            </div>
        </div>
    );
};
