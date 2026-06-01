/**
 * Research Agent — Main Application Logic
 * 
 * Initializes page-specific functionality based on the current route.
 * Handles form submissions, toast notifications, and global UI state.
 */

document.addEventListener('DOMContentLoaded', () => {
    initForms();
});


// ─── Form Handlers ───────────────────────────────────────────────

function initForms() {
    // Login Form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // Register Form
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    const errorEl = document.getElementById('login-error');

    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    if (!email || !password) {
        showFormError(errorEl, 'Please fill in all fields');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin h-5 w-5 mx-auto" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>';
    hideFormError(errorEl);

    try {
        await Auth.login(email, password);
        showToast('Login successful! Redirecting...', 'success');
        setTimeout(() => window.location.href = '/dashboard', 500);
    } catch (error) {
        showFormError(errorEl, error.message || 'Login failed');
        btn.disabled = false;
        btn.innerHTML = 'Sign In';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const btn = document.getElementById('register-btn');
    const errorEl = document.getElementById('register-error');

    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;

    if (!username || !email || !password) {
        showFormError(errorEl, 'Please fill in all fields');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin h-5 w-5 mx-auto" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>';
    hideFormError(errorEl);

    try {
        await Auth.register(username, email, password);
        showToast('Account created! Redirecting...', 'success');
        setTimeout(() => window.location.href = '/dashboard', 500);
    } catch (error) {
        const msg = error.errors?.length ? error.errors.join(', ') : (error.message || 'Registration failed');
        showFormError(errorEl, msg);
        btn.disabled = false;
        btn.innerHTML = 'Create Account';
    }
}


// ─── UI Helpers ──────────────────────────────────────────────────

function showFormError(el, message) {
    if (!el) return;
    el.textContent = message;
    el.classList.remove('hidden');
}

function hideFormError(el) {
    if (!el) return;
    el.classList.add('hidden');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const colors = {
        success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
        error: 'bg-red-500/10 border-red-500/20 text-red-400',
        info: 'bg-brand-500/10 border-brand-500/20 text-brand-400',
    };

    const toast = document.createElement('div');
    toast.className = `px-5 py-3 rounded-xl border backdrop-blur-xl text-sm font-medium shadow-xl animate-slide-up ${colors[type] || colors.info}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
