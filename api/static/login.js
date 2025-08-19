document.addEventListener('DOMContentLoaded', () => {
  // --- Theme management ---
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

  // --- Password toggle functionality ---
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

  // --- Toast notification system ---
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

  // --- Login form AJAX handling ---
  const form = document.getElementById('loginForm');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const formData = new FormData(form);

      try {
        const response = await fetch('/login', {
          method: 'POST',
          headers: { 'Accept': 'application/json' },
          body: formData
        });

        if (response.ok) {
          const data = await response.json();
          if (data.ok) {
            window.location.href = '/';
          } else {
            showToast(data.error || 'Login failed', 'bad');
          }
        } else {
          const data = await response.json().catch(() => ({}));
          showToast(data.error || 'Invalid credentials', 'bad');
        }
      } catch (error) {
        showToast('Network error. Please try again.', 'bad');
      }
    });
  }
});