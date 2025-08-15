// FIXED: Enhanced theme toggle functionality
document.addEventListener('DOMContentLoaded', () => {
  function initGlobalTheme() {
    // Get saved theme or default to dark
    let currentTheme = 'dark';
    try {
      const saved = localStorage.getItem('theme');
      if (saved) {
        currentTheme = saved;
        document.documentElement.setAttribute('data-theme', saved);
      }
    } catch(e) {
      console.warn('Could not access localStorage:', e);
    }
    
    const switcher = document.getElementById('themeSwitchGlobal');
    if (!switcher) return;
    
    // Update all logos and theme elements
    const updateTheme = (theme) => {
      const logoSrc = theme === 'light' ? '/static/logo-red.png' : '/static/logo.png';
      
      // Update all logos and backgrounds
      const elements = {
        navLogo: document.getElementById('navLogo'),
        sidebarLogo: document.getElementById('sidebarLogo'),
        dynamicBg: document.getElementById('dynamicLogoBg'),
        appBg: document.getElementById('appLogoBg')
      };
      
      Object.values(elements).forEach(el => {
        if (el) {
          if (el.tagName === 'IMG') {
            el.src = logoSrc;
          } else {
            el.style.backgroundImage = `url("${logoSrc}")`;
          }
        }
      });
      
      // Update switch state
      switcher.setAttribute('aria-checked', theme === 'light' ? 'true' : 'false');
      
      // Add visual feedback
      switcher.style.transform = 'scale(0.95)';
      setTimeout(() => {
        switcher.style.transform = 'scale(1)';
      }, 150);
    };
    
    // Toggle function
    const toggle = () => {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentTheme);
      
      try { 
        localStorage.setItem('theme', currentTheme); 
      } catch(e) {
        console.warn('Could not save to localStorage:', e);
      }
      
      updateTheme(currentTheme);
      
      // Show success toast
      if (window.showToast) {
        window.showToast(`Switched to ${currentTheme} theme`, 'good');
      }
    };
    
    // Bind events
    switcher.addEventListener('click', toggle);
    switcher.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggle();
      }
    });
    
    // Initial update
    updateTheme(currentTheme);
  }

  initGlobalTheme();

  // Global hamburger menu
  function initGlobalMenu() {
    const hamburger = document.getElementById('globalHamburger');
    const sidebar = document.getElementById('glassmorphicSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (!hamburger || !sidebar || !overlay) return;
    
    const openSidebar = () => {
      sidebar.classList.add('active');
      overlay.classList.add('active');
      hamburger.classList.add('active');
      hamburger.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    };
    
    const closeSidebar = () => {
      sidebar.classList.remove('active');
      overlay.classList.remove('active');
      hamburger.classList.remove('active');
      hamburger.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    };
    
    const toggleSidebar = () => {
      if (sidebar.classList.contains('active')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    };
    
    hamburger.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', closeSidebar);
    
    // Close on escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeSidebar();
    });
  }

  // Enhanced toast system
  function showToast(message, type = 'info') {
    const toastHost = document.getElementById('toastHost') || (() => {
      const host = document.createElement('div');
      host.id = 'toastHost';
      host.className = 'toast-host';
      document.body.appendChild(host);
      return host;
    })();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${type === 'good' ? '✅' : type === 'bad' ? '❌' : 'ℹ️'}</span>
      <span class="toast-message">${message}</span>
    `;
    toastHost.appendChild(toast);
    
    requestAnimationFrame(() => toast.classList.add('show'));
    
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Login form handling
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const formData = new FormData(loginForm);
      
      try {
        const response = await fetch('/login', {
          method: 'POST',
          headers: { 'Accept': 'application/json' },
          body: formData
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.ok) {
            showToast('Login successful!', 'good');
            // Minimal redirect - no complex animations
            setTimeout(() => {
              window.location.href = '/';
            }, 800);
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

  // Initialize everything else
  initGlobalMenu();
  
  // Make showToast globally available
  window.showToast = showToast;
});
