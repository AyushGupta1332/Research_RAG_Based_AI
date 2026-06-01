/**
 * Research Agent — API Client
 * 
 * Centralized HTTP client for all backend API calls.
 * Handles token injection, response parsing, and error handling.
 */

const API = {
    BASE_URL: '/api',

    /**
     * Make an authenticated API request.
     */
    async request(endpoint, options = {}) {
        const url = `${this.BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        // Inject auth token if available
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            const data = await response.json();

            if (!response.ok) {
                throw {
                    status: response.status,
                    message: data.message || 'Request failed',
                    errors: data.errors || [],
                };
            }

            return data;
        } catch (error) {
            if (error.status === 401) {
                // Try to refresh token
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    // Retry the original request
                    headers['Authorization'] = `Bearer ${localStorage.getItem('access_token')}`;
                    const retryResponse = await fetch(url, { ...options, headers });
                    return await retryResponse.json();
                } else {
                    // Refresh failed — logout
                    Auth.logout();
                }
            }
            throw error;
        }
    },

    /**
     * Refresh the access token using the refresh token.
     */
    async refreshToken() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return false;

        try {
            const response = await fetch(`${this.BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${refreshToken}`,
                },
            });

            if (!response.ok) return false;

            const data = await response.json();
            localStorage.setItem('access_token', data.data.access_token);
            return true;
        } catch {
            return false;
        }
    },

    // Convenience methods
    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    },

    put(endpoint, body) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body),
        });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },
};
