import React, { useState } from 'react';
import { apiFetch } from './api';
import { Link } from 'react-router-dom';

export const ResearchInbox: React.FC = () => {
    const [step, setStep] = useState<number>(0);
    const [inboxId, setInboxId] = useState<string | null>(null);
    const [companySymbol, setCompanySymbol] = useState<string | null>(null);
    const [extractedMarkdown, setExtractedMarkdown] = useState<string>('');
    const [diff, setDiff] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    
    // Step 1: Upload
    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        const file = e.target.files[0];
        
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            // Note: Since we are sending FormData, we shouldn't set Content-Type in apiFetch manually.
            // Using standard fetch here to bypass any json specific headers in apiFetch wrapper.
            const rawApiBase = (window as any).MRI_DEBUG?.API_BASE || '/api';
            const res = await fetch(`${rawApiBase}/research-inbox/items`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            setInboxId(data.inboxId);
            setStep(1); // Proceed to Detection
            await runPipeline(data.inboxId);
        } catch (err) {
            console.error(err);
            alert('Upload failed');
        } finally {
            setLoading(false);
        }
    };

    // Auto-run detection, parsing, and preview
    const runPipeline = async (id: string) => {
        try {
            setLoading(true);
            
            // 1. Detect Company
            const detectRes = await apiFetch(`research-inbox/items/${id}/detect-company`, { method: 'POST' });
            setCompanySymbol(detectRes.companySymbol);
            
            // 2. Duplicate Check
            await apiFetch(`research-inbox/items/${id}/duplicate-check`);
            
            // 3. Parse (Mocking MarkItDown)
            await apiFetch(`research-inbox/items/${id}/parse`, { method: 'POST' });
            
            // 4. Get Preview (Diff)
            const previewRes = await apiFetch(`research-inbox/items/${id}/preview`);
            setExtractedMarkdown(previewRes.extractedMarkdown);
            setDiff(previewRes.diff);
            
            setStep(2); // Preview Ready
        } catch (err) {
            console.error(err);
            alert('Pipeline failed');
        } finally {
            setLoading(false);
        }
    };

    // Step 5: Update Workspace
    const handleUpdate = async () => {
        if (!inboxId) return;
        setLoading(true);
        try {
            await apiFetch(`research-inbox/items/${inboxId}/update-workspace`, { method: 'POST' });
            setStep(3); // Success
        } catch (err) {
            console.error(err);
            alert('Update failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-black text-gray-200 p-8 font-sans">
            <div className="max-w-4xl mx-auto">
                <header className="mb-8 border-b border-gray-800 pb-4">
                    <h1 className="text-3xl font-bold text-white tracking-tight">Research Inbox</h1>
                    <p className="text-gray-500 mt-2">Process documents into structured company knowledge.</p>
                </header>

                {loading && <div className="text-indigo-400 mb-8 font-mono animate-pulse">Processing... Please wait.</div>}

                {/* Step 0: Upload */}
                {step === 0 && (
                    <div className="bg-gray-900 border border-gray-800 border-dashed rounded-lg p-12 text-center">
                        <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-500 text-white py-3 px-6 rounded font-semibold tracking-wide">
                            Select PDF Document
                            <input type="file" className="hidden" accept="application/pdf" onChange={handleUpload} />
                        </label>
                        <p className="text-gray-500 text-sm mt-4">Drop a MOSI report or research document here</p>
                    </div>
                )}

                {/* Step 1: Processing */}
                {step === 1 && (
                    <div className="bg-gray-900 border border-gray-800 rounded-lg p-8">
                        <h2 className="text-xl text-white mb-4">Pipeline Running</h2>
                        <ul className="space-y-3 text-sm text-gray-400 font-mono">
                            <li>✔ Inbox record created</li>
                            <li>Detecting company identity...</li>
                            <li>Running MarkItDown parsing...</li>
                            <li>Generating Workspace Diff...</li>
                        </ul>
                    </div>
                )}

                {/* Step 2: Preview Ready */}
                {step === 2 && !loading && (
                    <div className="space-y-8">
                        <div className="bg-emerald-900/30 border border-emerald-800 rounded-lg p-6 flex justify-between items-center">
                            <div>
                                <h2 className="text-xl text-white font-bold mb-1">Preview Ready: {companySymbol}</h2>
                                <p className="text-gray-400 text-sm">Review the extracted text and proposed workspace changes.</p>
                            </div>
                            <button 
                                onClick={handleUpdate}
                                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-6 rounded shadow-lg"
                            >
                                Update Company Knowledge
                            </button>
                        </div>

                        <div className="grid grid-cols-2 gap-6">
                            <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                                <h3 className="text-gray-400 uppercase tracking-widest text-xs font-semibold mb-4">Extracted Markdown (MarkItDown)</h3>
                                <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{extractedMarkdown}</pre>
                            </div>
                            
                            <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                                <h3 className="text-gray-400 uppercase tracking-widest text-xs font-semibold mb-4">Workspace Diff</h3>
                                <div className="space-y-4">
                                    {diff.map((op, idx) => (
                                        <div key={idx} className="bg-black border border-gray-800 p-4 rounded text-sm">
                                            <div className="flex justify-between mb-2">
                                                <span className="font-bold text-gray-300 uppercase">{op.node_type}</span>
                                                <span className={`text-xs px-2 py-1 rounded font-bold ${op.operation === 'CREATE' ? 'bg-emerald-900 text-emerald-400' : 'bg-blue-900 text-blue-400'}`}>
                                                    {op.operation}
                                                </span>
                                            </div>
                                            <p className="text-gray-400">{op.text}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 3: Success */}
                {step === 3 && (
                    <div className="bg-emerald-900/30 border border-emerald-800 rounded-lg p-10 text-center">
                        <div className="text-5xl mb-4">✅</div>
                        <h2 className="text-2xl text-white font-bold mb-2">Company Workspace Updated</h2>
                        <p className="text-gray-400 mb-8">The knowledge pipeline has successfully compounded the new insights for {companySymbol}.</p>
                        
                        <Link 
                            to={`/company/${companySymbol}`} 
                            className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-8 rounded shadow-lg inline-block"
                        >
                            Open Workspace
                        </Link>
                    </div>
                )}

            </div>
        </div>
    );
};
