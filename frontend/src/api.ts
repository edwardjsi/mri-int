// Parse API base safely to support separate frontend/backend deployments
function resolveApiBase(): string {
    const rawEnv = (import.meta.env.VITE_API_URL || '').replace(/['"]/g, '').trim();

    // 1. If no env var, or if the env var matches our current domain, 
    // ALWAYS use relative path '/api'. This is the safest way to avoid CORS/Mixed-Content.
    if (!rawEnv || rawEnv === '/api' || rawEnv.includes(window.location.hostname)) {
        return '/api';
    }

    // 2. If it is an external URL, ensure it has /api suffix
    let base = rawEnv;
    if (base.startsWith('http') && !base.toLowerCase().includes('/api')) {
        base = base.endsWith('/') ? `${base}api` : `${base}/api`;
    }
    return base.endsWith('/') ? base.slice(0, -1) : base;
}

const API_BASE = resolveApiBase();
console.log(`🚀 MRI Platform Booted | API_BASE: ${API_BASE} | Origin: ${window.location.origin}`);
(window as any).MRI_DEBUG = { API_BASE, origin: window.location.origin, build: '2026-03-24-v2' };

interface LoginResponse {
    access_token: string;
    token_type: string;
    client_id: string;
    name: string;
    email: string;
    is_admin: boolean;
}

function getToken(): string | null {
    return localStorage.getItem('mri_token');
}

function getClientName(): string {
    return localStorage.getItem('mri_name') || '';
}

function setAuth(data: LoginResponse) {
    localStorage.setItem('mri_token', data.access_token);
    localStorage.setItem('mri_client_id', data.client_id);
    localStorage.setItem('mri_name', data.name || 'User');
    localStorage.setItem('mri_email', data.email || '');
    localStorage.setItem('mri_is_admin', data.is_admin ? 'true' : 'false');
}

function clearAuth() {
    localStorage.removeItem('mri_token');
    localStorage.removeItem('mri_client_id');
    localStorage.removeItem('mri_name');
    localStorage.removeItem('mri_email');
    localStorage.removeItem('mri_is_admin');
}

function isAuthenticated(): boolean {
    return !!getToken();
}

function isAdmin(): boolean {
    return localStorage.getItem('mri_is_admin') === 'true';
}

async function apiFetch(path: string, options: RequestInit = {}, isLogin: boolean = false) {
    const token = getToken();
    
    // Normalize path to ensure it starts with /
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    const url = `${API_BASE}${normalizedPath}`;

    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...(options.headers as Record<string, string> || {}),
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    console.log(`📡 Fetching: ${options.method || 'GET'} ${url}`, options.body ? "(with body)" : "(no body)");

    const res = await fetch(url, { 
        ...options, 
        headers,
        // Removed mode: 'cors' to allow browser default behaviors for same-origin stability
    }).catch(err => {
        console.error("Network Error:", err);
        throw new Error(`Connection Error: ${err.message || 'Server unreachable'}`);
    });

    if (res.status === 401 && !isLogin) {
        clearAuth();
        window.location.reload();
        throw new Error('Session expired');
    }

        if (!res.ok) {
        let errorData: any;
        try {
            errorData = await res.json();
        } catch (e) {
            const text = await res.text().catch(() => 'No response body');
            console.error(`Status ${res.status} on URL [${url}] (Non-JSON):`, text);
            throw new Error(`DEBUG ${res.status} on ${url} -> ${text.substring(0, 40)}`);
        }

        console.error("API Error Response:", errorData);
        const detail = errorData.detail || 'Request failed';
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
        throw new Error(message);
    }

    return res.json();
}

// Auth
export const api = {
    register: (email: string, name: string, password: string, capital: number = 100000) =>
        apiFetch('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, name, password, initial_capital: capital }),
        }, true).then((data: LoginResponse) => { setAuth(data); return data; }),

    login: (email: string, password: string) =>
        apiFetch('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        }, true).then((data: LoginResponse) => { setAuth(data); return data; }),

    forgotPassword: (email: string) =>
        apiFetch('/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email }),
        }),

    resetPassword: (token: string, new_password: string) =>
        apiFetch('/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify({ token, new_password }),
        }),

    logout: () => { clearAuth(); window.location.reload(); },

    getProfile: () => apiFetch('/auth/me'),

    // Admin
    getAdminMetrics: () => apiFetch('/admin/metrics'),
    getAdminTopStocks: () => apiFetch('/admin/top-stocks'),

    // Signals
    getRegime: () => apiFetch('/signals/regime'),
    getTodaySignals: () => apiFetch('/signals/today'),
    getPendingSignals: () => apiFetch('/signals/pending'),
    getSignalHistory: (days: number = 30) => apiFetch(`/signals/history?days=${days}`),
    getScreener: (minScore: number = 4) => apiFetch(`/signals/screener?min_score=${minScore}`),

    // Actions
    recordAction: (signalId: string, actionTaken: string, actualPrice?: number, quantity?: number) =>
        apiFetch('/actions/record', {
            method: 'POST',
            body: JSON.stringify({ signal_id: signalId, action_taken: actionTaken, actual_price: actualPrice, quantity: quantity }),
        }),
    getActionHistory: () => apiFetch('/actions/history'),

    // Portfolio
    getPositions: () => apiFetch('/portfolio/positions'),
    getEquity: () => apiFetch('/portfolio/equity'),
    getPerformance: () => apiFetch('/portfolio/performance'),
    getDailySummary: () => apiFetch('/portfolio/daily-summary'),

    // Portfolio Review
    uploadPortfolioCsv: async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        // Include email from localStorage if available
        const email = localStorage.getItem('mri_email');
        const name = localStorage.getItem('mri_name') || 'User';
        if (email) {
            formData.append('email', email);
            formData.append('name', name);
        }

        const token = getToken();
        // Since this is Multipart, we don't set Content-Type JSON
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const normalizedPath = '/portfolio-review/upload-csv';
        const url = `${API_BASE}${normalizedPath}`;

        const res = await fetch(url, {
            method: 'POST',
            body: formData,
            headers,
            mode: 'cors'
        });
        if (res.status === 401) {
            clearAuth();
            window.location.reload();
            throw new Error('Session expired');
        }
        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail));
        }
        return res.json();
    },

    getSavedHoldings: () => apiFetch('/portfolio-review/holdings'),
    getHoldingsStatus: () => apiFetch('/portfolio-review/holdings-status'),

    saveHoldingsBulk: (holdings: { symbol: string, quantity: number, avg_cost: number }[]) =>
        apiFetch('/portfolio-review/save-bulk', {
            method: 'POST',
            body: JSON.stringify(holdings),
        }),

    deleteHolding: (symbol: string) =>
        apiFetch(`/portfolio-review/holdings/${symbol}`, {
            method: 'DELETE',
        }),

    deleteAllHoldings: () =>
        apiFetch('/portfolio-review/holdings/delete-all', {
            method: 'POST',
        }),

    regradeHoldings: (sendEmail: boolean = false) =>
        apiFetch(`/portfolio-review/holdings/regrade?send_email=${sendEmail ? 'true' : 'false'}`, {
            method: 'POST',
        }),

    regradeHoldingsSync: (sendEmail: boolean = false) =>
        apiFetch(`/portfolio-review/holdings/regrade-sync?send_email=${sendEmail ? 'true' : 'false'}`, {
            method: 'POST',
        }),

    // Capital
    addCapital: (amount: number) =>
        apiFetch('/auth/capital', {
            method: 'POST',
            body: JSON.stringify({ amount }),
        }),

    // Watchlist
    getWatchlist: () => apiFetch('/watchlist'),
    addToWatchlist: (symbol: string) =>
        apiFetch('/watchlist', {
            method: 'POST',
            body: JSON.stringify({ symbol }),
        }),
    removeFromWatchlist: (symbol: string) =>
        apiFetch(`/watchlist/${symbol}`, {
            method: 'DELETE',
        }),
    uploadWatchlistCsv: async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const token = getToken();
        // multipart so empty headers mapping
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const url = `${API_BASE}/watchlist/upload-csv`;

        const res = await fetch(url, {
            method: 'POST',
            body: formData,
            headers,
            mode: 'cors'
        });
        if (res.status === 401) {
            clearAuth();
            window.location.reload();
            throw new Error('Session expired');
        }
        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail));
        }
        return res.json();
    },

    // Health
    health: () => fetch(`${API_BASE}/health`).then(r => r.json()),
};

export { isAuthenticated, isAdmin, getClientName, clearAuth };
