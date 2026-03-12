const API_BASE = import.meta.env.VITE_API_URL || '/api';

interface LoginResponse {
    access_token: string;
    token_type: string;
    client_id: string;
    name: string;
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
    localStorage.setItem('mri_name', data.name);
}

function clearAuth() {
    localStorage.removeItem('mri_token');
    localStorage.removeItem('mri_client_id');
    localStorage.removeItem('mri_name');
}

function isAuthenticated(): boolean {
    return !!getToken();
}

async function apiFetch(path: string, options: RequestInit = {}) {
    const token = getToken();
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> || {}),
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
        clearAuth();
        window.location.reload();
        throw new Error('Session expired');
    }

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Request failed');
    }

    return res.json();
}

// Auth
export const api = {
    register: (email: string, name: string, password: string, capital: number = 100000) =>
        apiFetch('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, name, password, initial_capital: capital }),
        }).then((data: LoginResponse) => { setAuth(data); return data; }),

    login: (email: string, password: string) =>
        apiFetch('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        }).then((data: LoginResponse) => { setAuth(data); return data; }),

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
        const token = getToken();
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE}/portfolio-review/upload-csv`, {
            method: 'POST',
            body: formData,
            headers,
        });
        if (res.status === 401) {
            clearAuth();
            window.location.reload();
            throw new Error('Session expired');
        }
        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || 'Request failed');
        }
        return res.json();
    },

    getSavedHoldings: () => apiFetch('/portfolio-review/holdings'),

    saveHolding: (symbol: string, quantity: number, avg_cost: number) =>
        apiFetch('/portfolio-review/save', {
            method: 'POST',
            body: JSON.stringify({ symbol, quantity, avg_cost }),
        }),

    deleteHolding: (symbol: string) =>
        apiFetch(`/portfolio-review/holdings/${symbol}`, {
            method: 'DELETE',
        }),

    // Capital
    addCapital: (amount: number) =>
        apiFetch('/auth/capital', {
            method: 'POST',
            body: JSON.stringify({ amount }),
        }),

    // Health
    health: () => fetch(`${API_BASE}/health`).then(r => r.json()),
};

export { isAuthenticated, getClientName, clearAuth };
