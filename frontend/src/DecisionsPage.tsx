import { useState, useEffect } from 'react';
import { api } from './api';
import './App.css';

interface Decision {
  number: number;
  title: string;
  date: string | null;
  status: string | null;
  reason: string;
  raw: string;
}

export default function DecisionsPage({ onBack }: { onBack?: () => void }) {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const decisionsPerPage = 10;

  useEffect(() => {
    loadDecisions();
  }, []);

  const loadDecisions = async () => {
    try {
      setLoading(true);
      const res = await api.getDecisions({ limit: 200 });
      setDecisions(res.decisions || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load decisions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filteredDecisions = decisions.filter(d => 
    d.title.toLowerCase().includes(search.toLowerCase()) ||
    d.reason.toLowerCase().includes(search.toLowerCase()) ||
    String(d.number).includes(search)
  );

  const paginatedDecisions = filteredDecisions.slice(
    (currentPage - 1) * decisionsPerPage,
    currentPage * decisionsPerPage
  );

  const totalPages = Math.ceil(filteredDecisions.length / decisionsPerPage);

  const getStatusColor = (status: string | null) => {
    if (!status) return '#64748b';
    const s = status.toLowerCase();
    if (s.includes('final') && s.includes('executed')) return '#22c55e';
    if (s.includes('final')) return '#16a34a';
    if (s.includes('approved')) return '#3b82f6';
    if (s.includes('draft')) return '#f59e0b';
    if (s.includes('supersede')) return '#ef4444';
    if (s.includes('never')) return '#ef4444';
    return '#64748b';
  };

  const formatReason = (reason: string) => {
    // Clean up the reason text for display
    return reason
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  };

  return (
    <div className="decisions-page">
      <div className="decisions-header">
        {onBack && (
          <button className="btn-secondary" onClick={onBack} style={{ marginBottom: '16px' }}>
            ← Back to Dashboard
          </button>
        )}
        <h1 className="page-title">📋 Architectural Decisions Log</h1>
        <p className="page-subtitle">
          {filteredDecisions.length} of {decisions.length} decisions
          {search && ` (filtered by "${search}")`}
        </p>

        <div className="search-box" style={{ marginBottom: '24px' }}>
          <input
            type="text"
            placeholder="Search decisions by title, content, or number..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
            className="form-input"
            style={{ maxWidth: '400px' }}
          />
        </div>
      </div>

      {error && (
        <div className="error-alert" style={{ marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading">Loading decisions...</div>
      ) : filteredDecisions.length === 0 ? (
        <div className="empty-state">
          No decisions found{search ? ` matching "${search}"` : ''}.
        </div>
      ) : (
        <>
          <div className="decisions-list">
            {paginatedDecisions.map((decision) => (
              <div
                key={decision.number}
                className="decision-card"
                onClick={() => setSelectedDecision(decision)}
                style={{ cursor: 'pointer' }}
              >
                <div className="decision-header">
                  <div>
                    <span className="decision-number">#{decision.number}</span>
                    <h3 className="decision-title">{decision.title}</h3>
                  </div>
                  <span
                    className="decision-status"
                    style={{ backgroundColor: getStatusColor(decision.status) + '20', color: getStatusColor(decision.status), border: `1px solid ${getStatusColor(decision.status)}40` }}
                  >
                    {decision.status || 'UNKNOWN'}
                  </span>
                </div>
                {decision.date && (
                  <div className="decision-date">📅 {decision.date}</div>
                )}
                <div className="decision-reason-preview">
                  {formatReason(decision.reason).split('\n')[0]}
                  {formatReason(decision.reason).length > 100 && '...'}
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination" style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '24px' }}>
              <button
                className="btn-secondary"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </button>
              <span style={{ display: 'flex', alignItems: 'center', padding: '0 16px', color: '#94a3b8' }}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                className="btn-secondary"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* Modal for decision detail */}
      {selectedDecision && (
        <div className="modal-overlay" onClick={() => setSelectedDecision(null)}>
          <div className="modal-content modal-lg" onClick={e => e.stopPropagation()} style={{ maxWidth: '900px', maxHeight: '80vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <span className="decision-number" style={{ fontSize: '14px' }}>#{selectedDecision.number}</span>
                <h2 className="decision-title" style={{ marginTop: '4px' }}>{selectedDecision.title}</h2>
              </div>
              <button className="link-btn" onClick={() => setSelectedDecision(null)} style={{ fontSize: '24px' }}>&times;</button>
            </div>

            <div style={{ display: 'flex', gap: '24px', marginBottom: '16px', flexWrap: 'wrap' }}>
              {selectedDecision.date && (
                <span className="decision-date" style={{ fontSize: '14px' }}>📅 {selectedDecision.date}</span>
              )}
              <span
                className="decision-status"
                style={{
                  padding: '4px 12px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  backgroundColor: getStatusColor(selectedDecision.status) + '20',
                  color: getStatusColor(selectedDecision.status),
                  border: `1px solid ${getStatusColor(selectedDecision.status)}40`
                }}
              >
                {selectedDecision.status || 'UNKNOWN'}
              </span>
            </div>

            <div className="decision-content" style={{ whiteSpace: 'pre-wrap', fontSize: '13px', lineHeight: '1.6', color: '#cbd5e1' }}>
              {selectedDecision.raw}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}