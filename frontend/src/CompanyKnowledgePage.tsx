import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './App.css';

interface Fact {
    fact_id: string;
    entity_id: string;
    category: string;
    metric_name: string;
    value: number;
    unit: string;
    temporal_context: any;
    evidence: any;
    confidence: any;
    status: string;
    version: number;
}

interface Knowledge {
    entity_id: string;
    entity_name: string;
    business_model: any;
    management: any;
}

export const CompanyKnowledgePage: React.FC = () => {
    const { symbol: routeSymbol } = useParams<{ symbol: string }>();
    const navigate = useNavigate();
    
    const [symbol, setSymbol] = useState(routeSymbol || '');
    const [searchSymbol, setSearchSymbol] = useState(routeSymbol || '');
    const [library, setLibrary] = useState<any[]>([]);
    const [facts, setFacts] = useState<Fact[]>([]);
    const [knowledge, setKnowledge] = useState<Knowledge | null>(null);
    const [report, setReport] = useState<any>(null);
    const [manifest, setManifest] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    // Upload state
    const [uploadText, setUploadText] = useState('');
    const [uploading, setUploading] = useState(false);

    const fetchArtifacts = async (sym: string) => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`/api/v1/mosi/knowledge/${sym}`);
            if (!res.ok) {
                if (res.status === 404) {
                    throw new Error(`Knowledge not found for ${sym}. You can upload a MOSI report below.`);
                }
                throw new Error("Failed to load company knowledge.");
            }
            const data = await res.json();
            setFacts(data.company_facts);
            setKnowledge(data.company_knowledge);
            setReport(data.extraction_report);
            setManifest(data.knowledge_manifest);
        } catch (err: any) {
            setError(err.message || "Failed to load company knowledge.");
            setKnowledge(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const fetchLibrary = async () => {
            try {
                const res = await fetch('/api/v1/mosi/library');
                if (res.ok) {
                    const data = await res.json();
                    setLibrary(data.library);
                }
            } catch (err) {
                console.error("Failed to load MOSI library", err);
            }
        };
        fetchLibrary();
    }, []);

    useEffect(() => {
        if (routeSymbol) {
            setSymbol(routeSymbol);
            setSearchSymbol(routeSymbol);
        } else {
            setSymbol('');
            setSearchSymbol('');
        }
    }, [routeSymbol]);

    useEffect(() => {
        if (symbol) {
            fetchArtifacts(symbol);
        } else {
            setKnowledge(null);
            setError(null);
        }
    }, [symbol]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        const nextSymbol = searchSymbol.toUpperCase();
        setSymbol(nextSymbol);
        navigate(`/mosi/${nextSymbol}`);
    };

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!uploadText) return;
        
        setUploading(true);
        setError(null);
        try {
            const res = await fetch(`/api/v1/mosi/upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: symbol, report_text: uploadText })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Upload failed");
            
            // Re-fetch after successful upload
            setUploadText('');
            await fetchArtifacts(symbol);
        } catch (err: any) {
            setError(err.message || "Upload failed.");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="page-container dashboard-layout" style={{ display: 'flex', flexDirection: 'column', padding: '24px', overflowY: 'auto', gap: '24px' }}>
            {/* Search Bar */}
            <div className="card" style={{ padding: '16px', display: 'flex', gap: '16px', alignItems: 'center' }}>
                <h3 style={{ margin: 0, whiteSpace: 'nowrap' }}>Knowledge Base Lookup</h3>
                <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px', flex: 1 }}>
                    <input 
                        type="text" 
                        value={searchSymbol} 
                        onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
                        placeholder="Enter Ticker Symbol (e.g. GRANULES)"
                        className="form-input"
                        style={{ margin: 0 }}
                    />
                    <button type="submit" className="btn-primary" style={{ padding: '8px 16px' }}>Search</button>
                </form>
            </div>

            {!symbol && (
                <div className="card" style={{ padding: '24px' }}>
                    <h2 style={{ marginTop: 0 }}>MOSI Knowledge Library</h2>
                    <p style={{ color: 'var(--text-muted)' }}>Select a company below to view its compiled knowledge base artifacts.</p>
                    {library.length === 0 ? (
                        <p>No knowledge bases imported yet. Search for a symbol to begin importing.</p>
                    ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px', marginTop: '24px' }}>
                            {library.map((item) => (
                                <div key={item.symbol} 
                                     onClick={() => navigate(`/mosi/${item.symbol}`)}
                                     style={{ 
                                         padding: '16px', 
                                         border: '1px solid var(--border-color)', 
                                         borderRadius: '8px', 
                                         cursor: 'pointer',
                                         backgroundColor: 'var(--bg-secondary)',
                                         transition: 'transform 0.2s, borderColor 0.2s'
                                     }}
                                     onMouseEnter={(e) => e.currentTarget.style.borderColor = '#10b981'}
                                     onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-color)'}
                                >
                                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#60a5fa', marginBottom: '8px' }}>{item.symbol}</div>
                                    <div style={{ fontSize: '14px', marginBottom: '8px' }}>{item.entity_name}</div>
                                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                        Updated: {item.updated_at ? new Date(item.updated_at).toLocaleDateString() : 'Unknown'}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {symbol && loading && <p>Loading Company Knowledge Base...</p>}
            
            {symbol && error && (
                <div className="card" style={{ padding: '20px', backgroundColor: '#ef444415', border: '1px solid #ef4444' }}>
                    <p className="error-text" style={{ margin: '0 0 16px 0' }}>{error}</p>
                    
                    {error.includes("not found") && (
                        <form onSubmit={handleUpload}>
                            <h4 style={{ marginTop: 0 }}>Upload MOSI Report for {symbol}</h4>
                            <textarea 
                                value={uploadText}
                                onChange={(e) => setUploadText(e.target.value)}
                                placeholder="Paste the full MOSI markdown text here..."
                                className="form-input"
                                rows={10}
                                style={{ width: '100%', fontFamily: 'monospace' }}
                            />
                            <button type="submit" className="btn-primary" disabled={uploading} style={{ marginTop: '12px' }}>
                                {uploading ? 'Compiling & Importing...' : 'Run Compiler & Import'}
                            </button>
                        </form>
                    )}
                </div>
            )}

            {!loading && !error && knowledge && (
                <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1 style={{ margin: '0 0 8px 0', fontSize: '28px', fontWeight: '600' }}>{knowledge.entity_name}</h1>
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <span className="badge" style={{ backgroundColor: '#10b981', color: 'white' }}>VALIDATED</span>
                        <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Version {manifest?.knowledge_version}</span>
                        <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>Updated: {new Date(manifest?.last_updated).toLocaleString()}</span>
                    </div>
                </div>
            </div>

            {/* Knowledge Overview */}
            <div className="card" style={{ padding: '20px' }}>
                <h3 style={{ marginTop: 0, borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>Business Model</h3>
                <p>{knowledge.business_model.narrative_summary}</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginTop: '16px' }}>
                    <div>
                        <strong>Products:</strong>
                        <ul style={{ paddingLeft: '20px', marginTop: '4px' }}>
                            {knowledge.business_model.structured_entities.products.map((p: string) => <li key={p}>{p}</li>)}
                        </ul>
                    </div>
                    <div>
                        <strong>Plants:</strong>
                        <ul style={{ paddingLeft: '20px', marginTop: '4px' }}>
                            {knowledge.business_model.structured_entities.plants.map((p: string) => <li key={p}>{p}</li>)}
                        </ul>
                    </div>
                    <div>
                        <strong>Customer Segments:</strong>
                        <ul style={{ paddingLeft: '20px', marginTop: '4px' }}>
                            {knowledge.business_model.structured_entities.customer_segments.map((p: string) => <li key={p}>{p}</li>)}
                        </ul>
                    </div>
                </div>
            </div>

            {/* Management */}
            <div className="card" style={{ padding: '20px' }}>
                <h3 style={{ marginTop: 0, borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>Management</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    {Object.entries(knowledge.management).map(([key, val]: [string, any]) => {
                        if (key === 'key_executives') return null;
                        return (
                            <div key={key}>
                                <strong style={{ textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}:</strong>
                                <p style={{ margin: '4px 0' }}>{val.narrative}</p>
                            </div>
                        );
                    })}
                </div>
                <div style={{ marginTop: '16px' }}>
                    <strong>Key Executives:</strong>
                    <ul style={{ paddingLeft: '20px', marginTop: '4px' }}>
                        {knowledge.management.key_executives.map((e: any) => (
                            <li key={e.entity_id}>{e.name} ({e.role})</li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Facts & Evidence */}
            <div className="card" style={{ padding: '20px' }}>
                <h3 style={{ marginTop: 0, borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>Extracted Facts & Evidence</h3>
                <table className="data-table" style={{ width: '100%' }}>
                    <thead>
                        <tr>
                            <th>Fact ID</th>
                            <th>Metric</th>
                            <th>Value</th>
                            <th>Context</th>
                            <th>Confidence</th>
                            <th>Evidence Quote</th>
                        </tr>
                    </thead>
                    <tbody>
                        {facts.map(f => (
                            <tr key={f.fact_id}>
                                <td>{f.fact_id}</td>
                                <td>{f.metric_name}</td>
                                <td>{f.value} {f.unit}</td>
                                <td>{f.temporal_context.period_label}</td>
                                <td>
                                    {(f.confidence.value * 100).toFixed(0)}% <br/>
                                    <span style={{fontSize: '11px', color: 'var(--text-muted)'}}>{f.confidence.reason}</span>
                                </td>
                                <td>
                                    <em style={{ fontSize: '13px' }}>"{f.evidence.quote}"</em>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Compiler Report */}
            <div className="card" style={{ padding: '20px', backgroundColor: '#1e293b' }}>
                <h3 style={{ marginTop: 0, color: 'white', borderBottom: '1px solid #334155', paddingBottom: '12px' }}>Compiler Report</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', color: '#cbd5e1' }}>
                    <div>
                        <strong>Execution Time</strong>
                        <div style={{ fontSize: '20px', color: 'white' }}>{report.execution_time_ms}ms</div>
                    </div>
                    <div>
                        <strong>Coverage</strong>
                        <div style={{ fontSize: '20px', color: '#10b981' }}>{report.coverage_pct}%</div>
                    </div>
                    <div>
                        <strong>Missing Fields</strong>
                        <div style={{ fontSize: '20px', color: report.missing_fields > 0 ? '#ef4444' : 'white' }}>{report.missing_fields}</div>
                    </div>
                    <div>
                        <strong>Hallucinations</strong>
                        <div style={{ fontSize: '20px', color: report.hallucinations_flagged > 0 ? '#ef4444' : '#10b981' }}>{report.hallucinations_flagged}</div>
                    </div>
                </div>
            </div>
            </>
            )}
        </div>
    );
};
