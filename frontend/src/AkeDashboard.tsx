import React, { useState, useEffect } from 'react';
import { apiFetch } from './api';

interface VariableCandidate {
    id: string;
    rawName: string;
    canonicalName: string;
    section: string;
    dataType: string;
    confidence: number;
    occurrences: number;
    companies: string[];
    aliases: string[];
    status: string;
}

export const AkeDashboard: React.FC = () => {
    const [candidates, setCandidates] = useState<VariableCandidate[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchReserveVariables = async () => {
        try {
            setLoading(true);
            const data = await apiFetch('extractor/variables/reserve');
            setCandidates(data);
        } catch (err) {
            console.error("Failed to load candidates", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchReserveVariables();
    }, []);

    const handlePromote = async (id: string) => {
        try {
            await apiFetch(`extractor/variables/${id}/promote`, { method: 'POST' });
            fetchReserveVariables();
        } catch (err) {
            console.error("Failed to promote", err);
        }
    };

    const handleReject = async (id: string) => {
        try {
            await apiFetch(`extractor/variables/${id}/reject`, { method: 'POST' });
            fetchReserveVariables();
        } catch (err) {
            console.error("Failed to reject", err);
        }
    };

    return (
        <div className="min-h-screen bg-black text-gray-200 p-8 font-sans">
            <div className="max-w-5xl mx-auto">
                <header className="mb-10">
                    <h1 className="text-3xl font-bold text-white tracking-tight">Adaptive Knowledge Extractor (AKE)</h1>
                    <p className="text-gray-500 mt-2">Human Review Queue for Variable Promotion</p>
                </header>

                {loading ? (
                    <div className="text-indigo-400 font-mono animate-pulse">Loading candidates...</div>
                ) : candidates.length === 0 ? (
                    <div className="bg-gray-900 border border-gray-800 rounded-lg p-12 text-center text-gray-500">
                        No variables currently awaiting review.
                    </div>
                ) : (
                    <div className="space-y-6">
                        {candidates.map(candidate => (
                            <div key={candidate.id} className="bg-gray-900 border border-indigo-900/50 rounded-lg p-6">
                                <div className="flex justify-between items-start mb-6">
                                    <div>
                                        <h2 className="text-2xl text-white font-bold mb-1">{candidate.rawName}</h2>
                                        <div className="flex gap-4 text-sm text-gray-400">
                                            <span><strong className="text-gray-300">Section:</strong> {candidate.section}</span>
                                            <span><strong className="text-gray-300">Occurrences:</strong> {candidate.occurrences}</span>
                                            <span><strong className="text-gray-300">Confidence:</strong> {(candidate.confidence * 100).toFixed(0)}%</span>
                                        </div>
                                    </div>
                                    <div className="bg-indigo-900/30 text-indigo-400 text-xs px-3 py-1 rounded font-bold uppercase tracking-wider">
                                        Awaiting Review
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-8 mb-6 border-t border-gray-800 pt-6">
                                    <div>
                                        <h3 className="text-xs text-gray-500 uppercase tracking-widest mb-2">Discovered In</h3>
                                        <div className="flex flex-wrap gap-2">
                                            {candidate.companies.map(c => (
                                                <span key={c} className="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded">{c}</span>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <h3 className="text-xs text-gray-500 uppercase tracking-widest mb-2">Suggested Canonical Name</h3>
                                        <div className="font-mono text-emerald-400 bg-emerald-900/20 inline-block px-3 py-1 rounded border border-emerald-800/50">
                                            {candidate.canonicalName}
                                        </div>
                                        {candidate.aliases.length > 0 && (
                                            <div className="mt-3">
                                                <h3 className="text-xs text-gray-500 uppercase tracking-widest mb-1">Aliases Merge</h3>
                                                <div className="text-sm text-gray-400 line-through">
                                                    {candidate.aliases.join(", ")}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="flex gap-3 border-t border-gray-800 pt-4">
                                    <button 
                                        onClick={() => handlePromote(candidate.id)}
                                        className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-6 rounded text-sm transition-colors"
                                    >
                                        Approve & Promote
                                    </button>
                                    <button 
                                        className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-6 rounded text-sm transition-colors"
                                    >
                                        Merge Alias...
                                    </button>
                                    <button 
                                        onClick={() => handleReject(candidate.id)}
                                        className="bg-gray-800 hover:bg-red-900/50 hover:text-red-400 text-gray-400 font-bold py-2 px-6 rounded text-sm transition-colors"
                                    >
                                        Reject
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
