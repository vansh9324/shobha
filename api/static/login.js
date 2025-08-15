document.addEventListener('DOMContentLoaded', () => {
  // Theme management
  function initTheme() {
    try {
      const saved = localStorage.getItem('theme');
      if (saved) document.documentElement.setAttribute('data-theme', saved);
    } catch(e) {}
    
    const switcher = document.getElementById('themeSwitchGlobal');
    if (!switcher) return;
    
    const updateState = () => {
      const theme = document.documentElement.getAttribute('data-theme') || 'dark';
      switcher.setAttribute('aria-checked', theme === 'light' ? 'true' : 'false');
      
      const navLogo = document.getElementById('navLogo');
      if (navLogo) {
        navLogo.src = theme === 'light' ? '/static/logo-red.png' : '/static/logo.png';
      }
    };
    
    const toggle = () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { 
        localStorage.setItem('theme', next); 
      } catch(e) {}
      updateState();
    };
    
    switcher.addEventListener('click', toggle);
    switcher.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggle();
      }
    });
    
    updateState();
  }

  initTheme();

  // Simple toast system
  function showToast(message, type = 'bad') {
    const toastHost = document.getElementById('toastHost');
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

  // Minimal form handling
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
            // Minimal success - just redirect
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