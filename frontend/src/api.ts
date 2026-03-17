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
    localStorage.setItem('mri_name', data.name || 'User');
}

function clearAuth() {
    localStorage.removeItem('mri_token');
    localStorage.removeItem('mri_client_id');
    localStorage.removeItem('mri_name');
}

function isAuthenticated(): boolean {
    return !!getToken();
}

async function apiFetch(path: string, options: RequestInit = {}, isLogin: boolean = false) {
    const token = getToken();
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> || {}),
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers }).catch(err => {
        // Network errors (e.g. server down)
        console.error("Network Error:", err);
        throw new Error(`Cloud Connection Error: ${err.message || 'Server unreachable'}`);
    });

    // Handle 401 Session Expired (except during login itself)
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
            // Not JSON (e.g. 500 HTML error page)
            const text = await res.text().catch(() => 'No response body');
            console.error("Server Error (Non-JSON):", text);
            throw new Error(`Server Error (${res.status}): ${text.substring(0, 100)}`);
        }

        const detail = errorData.detail || 'Request failed';
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
        console.error("API Error Response:", errorData);
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
            const detail = error.detail || 'Request failed';
            const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
            throw new Error(message);
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

    // Health
    health: () => fetch(`${API_BASE}/health`).then(r => r.json()),
};

export { isAuthenticated, getClientName, clearAuth };
