document.addEventListener('DOMContentLoaded', () => {
  // --- NEW: Backend Configuration ---
  const API_BASE_URL = 'https://shobha-backend.onrender.com';

  // --- Theme management (UNCHANGED) ---
  function initTheme() {
      // Set theme from localStorage if available (using universal key)
      try {
          const saved = localStorage.getItem('shobha_theme'); // Changed from 'theme' to 'shobha_theme'
          if (saved) document.documentElement.setAttribute('data-theme', saved);
      } catch (e) {}

      // Find all theme switchers (login and global)
      const switchers = [
          document.getElementById('themeSwitchGlobal'),
          document.getElementById('themeSwitchLogin')
      ].filter(Boolean);

      if (!switchers.length) return;

      // Update switch state and logo
      const updateState = () => {
          const theme = document.documentElement.getAttribute('data-theme') || 'dark';
          switchers.forEach(sw => {
              sw.setAttribute('aria-checked', theme === 'light' ? 'true' : 'false');
          });

          // Update all nav logos (login and navbar)
          const navLogos = [
              document.getElementById('navLogo'),
              document.getElementById('loginLogo')
          ].filter(Boolean);

          navLogos.forEach(logo => {
              logo.src = theme === 'light' ? '/static/logo-red.png' : '/static/logo.png';
          });
      };

      // Toggle theme and persist
      const toggle = () => {
          const current = document.documentElement.getAttribute('data-theme') || 'dark';
          const next = current === 'dark' ? 'light' : 'dark';
          document.documentElement.setAttribute('data-theme', next);
          try {
              localStorage.setItem('shobha_theme', next); // Changed from 'theme' to 'shobha_theme'
          } catch (e) {}
          updateState();
      };

      // Attach event listeners to all switchers
      switchers.forEach(sw => {
          sw.addEventListener('click', toggle);
          sw.addEventListener('keydown', (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggle();
              }
          });
      });

      updateState();
  }

  initTheme();

  // --- Password toggle functionality (UNCHANGED) ---
  function initPasswordToggle() {
      const passwordToggle = document.getElementById('passwordToggle');
      const passwordInput = document.getElementById('password');
      const passwordIcon = document.getElementById('passwordIcon');

      if (passwordToggle && passwordInput && passwordIcon) {
          passwordToggle.addEventListener('click', () => {
              const isPassword = passwordInput.type === 'password';
              passwordInput.type = isPassword ? 'text' : 'password';
              passwordIcon.textContent = isPassword ? '🙈' : '👁️';
              passwordToggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
          });

          // Also handle keyboard activation
          passwordToggle.addEventListener('keydown', (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  passwordToggle.click();
              }
          });
      }
  }

  initPasswordToggle();

  // --- Toast notification system (UNCHANGED) ---
  function showToast(message, type = 'bad') {
      const toastHost = document.getElementById('toastHost');
      if (!toastHost) return;

      const toast = document.createElement('div');
      toast.className = `toast ${type}`;
      toast.textContent = message;
      toastHost.appendChild(toast);

      requestAnimationFrame(() => toast.classList.add('show'));

      setTimeout(() => {
          toast.classList.remove('show');
          setTimeout(() => toast.remove(), 200);
      }, 2500);
  }

  // --- NEW: JWT Token Management ---
  function storeToken(token) {
      try {
          localStorage.setItem('jwt_token', token);
      } catch (e) {
          console.warn('Failed to store JWT token');
      }
  }

  function isAuthenticated() {
      try {
          return !!localStorage.getItem('jwt_token');
      } catch (e) {
          return false;
      }
  }

  // --- NEW: Keep-alive service ---
  function startKeepAlive() {
      const ping = () => {
          fetch(`${API_BASE_URL}/api/v1/health`).catch(() => {});
      };
      ping(); // Initial ping
      setInterval(ping, 14 * 60 * 1000); // Every 14 minutes
  }
  startKeepAlive();

  // --- Login form AJAX handling (UPDATED for JWT) ---
  const form = document.getElementById('loginForm');
  if (form) {
      form.addEventListener('submit', async (e) => {
          e.preventDefault();
          const formData = new FormData(form);

          try {
              // CHANGED: Use new backend endpoint
              const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
                  method: 'POST',
                  body: formData // Backend expects FormData, not JSON
              });

              if (response.ok) {
                  const data = await response.json();
                  if (data.access_token) {
                      // NEW: Store JWT token instead of relying on session
                      storeToken(data.access_token);
                      showToast('Login successful!', 'good');
                      setTimeout(() => window.location.href = '/', 1000);
                  } else {
                      showToast('Login failed', 'bad');
                  }
              } else {
                  const data = await response.json().catch(() => ({}));
                  showToast(data.detail || 'Invalid credentials', 'bad');
              }
          } catch (error) {
              showToast('Network error. Please try again.', 'bad');
          }
      });
  }

  // --- NEW: Expose global functions for other files ---
  window.showToast = showToast;
  window.isAuthenticated = isAuthenticated;
  window.API_BASE_URL = API_BASE_URL;
});
