/**
 * Research Agent — Authentication Module
 * 
 * Handles login, register, logout, and token management.
 */

const Auth = {
    /**
     * Check if user is authenticated (has a valid token).
     */
    isAuthenticated() {
        return !!localStorage.getItem('access_token');
    },

    /**
     * Get the stored user data.
     */
    getUser() {
        const userData = localStorage.getItem('user');
        return userData ? JSON.parse(userData) : null;
    },

    /**
     * Store authentication data after login/register.
     */
    setAuth(data) {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        if (data.user) {
            localStorage.setItem('user', JSON.stringify(data.user));
        }
    },

    /**
     * Clear all auth data and redirect to login.
     */
    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
    },

    /**
     * Register a new user.
     */
    async register(username, email, password) {
        const data = await API.post('/auth/register', { username, email, password });
        this.setAuth(data.data);
        return data;
    },

    /**
     * Login with email and password.
     */
    async login(email, password) {
        const data = await API.post('/auth/login', { email, password });
        this.setAuth(data.data);
        return data;
    },
};
