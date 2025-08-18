/**
 * Global JavaScript utilities for Shobha Sarees Photo Maker
 * Handles theme management, global UI interactions, and shared functionality
 */

// ========== GLOBAL CONFIGURATION ==========
const GLOBAL_CONFIG = {
    theme: {
        storage_key: 'shobha_theme',
        default: 'dark',
        switch_duration: 300
    },
    sidebar: {
        breakpoint: 768,
        overlay_class: 'sidebar-overlay'
    },
    performance: {
        debounce_delay: 150,
        throttle_delay: 16
    }
};

// ========== THEME MANAGEMENT ==========
class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme();
        this.switches = [];
        this.logos = [];
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.bindThemeSwitches();
        this.updateLogos();
        
        // Listen for system theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)')
                .addEventListener('change', (e) => this.onSystemThemeChange(e));
        }
        
        console.log('✅ ThemeManager initialized');
    }

    getStoredTheme() {
        try {
            return localStorage.getItem(GLOBAL_CONFIG.theme.storage_key) || 
                   this.getSystemTheme() || 
                   GLOBAL_CONFIG.theme.default;
        } catch (e) {
            console.warn('LocalStorage unavailable, using default theme');
            return GLOBAL_CONFIG.theme.default;
        }
    }

    getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
            return 'light';
        }
        return null;
    }

    storeTheme(theme) {
        try {
            localStorage.setItem(GLOBAL_CONFIG.theme.storage_key, theme);
        } catch (e) {
            console.warn('Failed to store theme preference');
        }
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        this.storeTheme(theme);
        this.updateThemeSwitches(theme);
        this.updateLogos();
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
        
        // Show feedback
        if (window.showToast) {
            window.showToast(`Switched to ${newTheme} theme`, 'good');
        }
        
        return newTheme;
    }

    bindThemeSwitches() {
        const switches = document.querySelectorAll('[role="switch"][aria-label*="theme"], .theme-switch');
        
        switches.forEach(switchEl => {
            this.switches.push(switchEl);
            
            // Click handler
            switchEl.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleTheme();
            });
            
            // Keyboard handler
            switchEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleTheme();
                }
            });
        });
    }

    updateThemeSwitches(theme) {
        this.switches.forEach(switchEl => {
            const isLight = theme === 'light';
            switchEl.setAttribute('aria-checked', isLight.toString());
            
            // Update visual state if needed
            if (isLight) {
                switchEl.classList.add('light');
            } else {
                switchEl.classList.remove('light');
            }
        });
    }

    updateLogos() {
        const logoSrc = this.currentTheme === 'light' ? '/static/logo-red.png' : '/static/logo.png';
        
        // Update all logo images
        const logos = document.querySelectorAll('.nav-logo, .sidebar-logo-improved, #navLogo, #sidebarLogo');
        logos.forEach(logo => {
            if (logo && logo.src !== logoSrc) {
                logo.src = logoSrc;
            }
        });

        // Update background logo
        const appBg = document.getElementById('appLogoBg');
        if (appBg) {
            appBg.style.backgroundImage = `url("${logoSrc}")`;
        }
    }

    onSystemThemeChange(e) {
        // Only auto-switch if user hasn't manually set a theme
        const storedTheme = localStorage.getItem(GLOBAL_CONFIG.theme.storage_key);
        if (!storedTheme) {
            const newTheme = e.matches ? 'dark' : 'light';
            this.applyTheme(newTheme);
        }
    }
}

// ========== SIDEBAR MANAGEMENT ==========
class SidebarManager {
    constructor() {
        this.sidebar = null;
        this.overlay = null;
        this.hamburger = null;
        this.isOpen = false;
        this.touchStartX = 0;
        this.touchStartY = 0;
        
        this.init();
    }

    init() {
        this.cacheDOMElements();
        
        if (!this.sidebar || !this.hamburger) {
            console.warn('Sidebar elements not found, skipping initialization');
            return;
        }

        this.bindEvents();
        this.setupSwipeGestures();
        
        console.log('✅ SidebarManager initialized');
    }

    cacheDOMElements() {
        this.sidebar = document.getElementById('glassmorphicSidebar');
        this.overlay = document.getElementById('sidebarOverlay') || this.createOverlay();
        this.hamburger = document.getElementById('globalHamburger');
    }

    createOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'sidebarOverlay';
        overlay.className = 'sidebar-overlay';
        overlay.setAttribute('aria-hidden', 'true');
        document.body.appendChild(overlay);
        return overlay;
    }

    bindEvents() {
        // Hamburger click
        this.hamburger.addEventListener('click', () => this.toggle());
        
        // Overlay click
        this.overlay.addEventListener('click', () => this.close());
        
        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
        
        // Resize handler
        window.addEventListener('resize', this.debounce(() => {
            if (window.innerWidth > GLOBAL_CONFIG.sidebar.breakpoint && this.isOpen) {
                this.close();
            }
        }, GLOBAL_CONFIG.performance.debounce_delay));
    }

    setupSwipeGestures() {
        if (!('ontouchstart' in window)) return;

        // Touch start
        document.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches.clientY;
        }, { passive: true });

        // Touch move for swipe detection
        document.addEventListener('touchmove', (e) => {
            if (!this.touchStartX || !this.touchStartY) return;

            const touchEndX = e.touches[0].clientX;
            const touchEndY = e.touches.clientY;
            
            const diffX = this.touchStartX - touchEndX;
            const diffY = this.touchStartY - touchEndY;

            // Only trigger on horizontal swipes
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
                if (diffX > 0 && this.isOpen) {
                    // Swipe left to close
                    this.close();
                } else if (diffX < 0 && !this.isOpen && this.touchStartX < 50) {
                    // Swipe right from left edge to open
                    this.open();
                }
                
                this.touchStartX = 0;
                this.touchStartY = 0;
            }
        }, { passive: true });
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        if (this.isOpen) return;

        this.sidebar.classList.add('active');
        this.overlay.classList.add('active');
        this.hamburger.classList.add('active');
        
        // Update ARIA states
        this.hamburger.setAttribute('aria-expanded', 'true');
        this.sidebar.setAttribute('aria-hidden', 'false');
        this.overlay.setAttribute('aria-hidden', 'false');
        
        // Prevent body scroll on mobile
        document.body.style.overflow = 'hidden';
        
        // Focus management
        const firstFocusable = this.sidebar.querySelector('a, button');
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
        
        this.isOpen = true;
    }

    close() {
        if (!this.isOpen) return;

        this.sidebar.classList.remove('active');
        this.overlay.classList.remove('active');
        this.hamburger.classList.remove('active');
        
        // Update ARIA states
        this.hamburger.setAttribute('aria-expanded', 'false');
        this.sidebar.setAttribute('aria-hidden', 'true');
        this.overlay.setAttribute('aria-hidden', 'true');
        
        // Restore body scroll
        document.body.style.overflow = '';
        
        // Return focus to hamburger
        this.hamburger.focus();
        
        this.isOpen = false;
    }

    // Utility function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// ========== TOAST NOTIFICATION SYSTEM ==========
class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = new Map();
        this.nextId = 1;
        this.init();
    }

    init() {
        this.createContainer();
        console.log('✅ ToastManager initialized');
    }

    createContainer() {
        this.container = document.getElementById('toastHost');
        
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toastHost';
            this.container.className = 'toast-host';
            this.container.setAttribute('aria-live', 'polite');
            this.container.setAttribute('aria-atomic', 'true');
            document.body.appendChild(this.container);
        }
    }

    show(message, type = 'info', duration = null) {
        const id = this.nextId++;
        
        // Default durations based on type
        if (!duration) {
            duration = {
                'good': 3000,
                'info': 3000,
                'bad': 5000,
                'warning': 4000
            }[type] || 3000;
        }

        // Create toast element
        const toast = this.createElement(message, type, id);
        
        // Add to container
        this.container.appendChild(toast);
        this.toasts.set(id, toast);
        
        // Show animation
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // Auto remove
        setTimeout(() => this.remove(id), duration);
        
        // Click to dismiss
        toast.addEventListener('click', () => this.remove(id));
        
        return id;
    }

    createElement(message, type, id) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.setAttribute('data-toast-id', id);
        toast.setAttribute('role', 'alert');
        
        const icons = {
            good: '✅',
            bad: '❌',
            info: 'ℹ️',
            warning: '⚠️'
        };
        
        toast.innerHTML = `
            <span class="toast-icon" aria-hidden="true">${icons[type] || 'ℹ️'}</span>
            <span class="toast-message">${this.escapeHtml(message)}</span>
        `;
        
        return toast;
    }

    remove(id) {
        const toast = this.toasts.get(id);
        if (!toast) return;

        toast.classList.remove('show');
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            this.toasts.delete(id);
        }, 300); // Match CSS transition duration
    }

    clear() {
        this.toasts.forEach((toast, id) => this.remove(id));
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }
}

// ========== ACCESSIBILITY ENHANCEMENTS ==========
class AccessibilityManager {
    constructor() {
        this.init();
    }

    init() {
        this.enhanceFocusManagement();
        this.setupSkipLinks();
        this.addKeyboardSupport();
        this.setupScreenReaderSupport();
        
        console.log('✅ AccessibilityManager initialized');
    }

    enhanceFocusManagement() {
        // Enhanced focus indicators
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });

        // Focus trap for modals
        this.setupFocusTraps();
    }

    setupSkipLinks() {
        const skipLinks = document.querySelectorAll('.skip-link');
        
        skipLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const target = document.getElementById(targetId);
                
                if (target) {
                    target.focus();
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

    addKeyboardSupport() {
        // Add keyboard support to clickable elements without proper semantics
        const clickables = document.querySelectorAll('.dropzone-glass, .card, [role="button"]:not(button)');
        
        clickables.forEach(el => {
            if (!el.hasAttribute('tabindex')) {
                el.setAttribute('tabindex', '0');
            }
            
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    el.click();
                }
            });
        });
    }

    setupScreenReaderSupport() {
        // Announce page changes
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.id = 'page-announcer';
        document.body.appendChild(announcer);
        
        window.announceToScreenReader = (message) => {
            announcer.textContent = message;
            setTimeout(() => announcer.textContent = '', 1000);
        };
    }

    setupFocusTraps() {
        const modals = document.querySelectorAll('[role="dialog"], .modal');
        
        modals.forEach(modal => {
            modal.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    this.trapFocus(e, modal);
                }
            });
        });
    }

    trapFocus(e, container) {
        const focusableElements = container.querySelectorAll(
            'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select'
        );
        
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
        }
    }
}

// ========== PERFORMANCE UTILITIES ==========
class PerformanceManager {
    constructor() {
        this.metrics = {
            pageLoadTime: 0,
            domLoadTime: 0,
            resourceCount: 0
        };
        this.init();
    }

    init() {
        this.measurePageLoad();
        this.setupLazyLoading();
        this.setupIntersectionObserver();
        
        console.log('✅ PerformanceManager initialized');
    }

    measurePageLoad() {
        window.addEventListener('load', () => {
            if (performance && performance.timing) {
                const timing = performance.timing;
                this.metrics.pageLoadTime = timing.loadEventEnd - timing.navigationStart;
                this.metrics.domLoadTime = timing.domContentLoadedEventEnd - timing.navigationStart;
                
                console.log(`📊 Page load metrics:`, this.metrics);
            }
        });
    }

    setupLazyLoading() {
        // Intersection Observer for lazy loading
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                        }
                        img.classList.remove('lazy');
                        observer.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    setupIntersectionObserver() {
        // Generic intersection observer for animations
        if ('IntersectionObserver' in window) {
            const animationObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            });

            document.querySelectorAll('.animate-on-scroll').forEach(el => {
                animationObserver.observe(el);
            });
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// ========== INITIALIZATION ==========
class GlobalApp {
    constructor() {
        this.themeManager = null;
        this.sidebarManager = null;
        this.toastManager = null;
        this.accessibilityManager = null;
        this.performanceManager = null;
        
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeManagers());
        } else {
            this.initializeManagers();
        }
    }

    initializeManagers() {
        try {
            this.themeManager = new ThemeManager();
            this.sidebarManager = new SidebarManager();
            this.toastManager = new ToastManager();
            this.accessibilityManager = new AccessibilityManager();
            this.performanceManager = new PerformanceManager();
            
            // Expose global functions
            this.exposeGlobalFunctions();
            
            console.log('✅ Global app initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize global app:', error);
        }
    }

    exposeGlobalFunctions() {
        // Expose toast function globally
        window.showToast = (message, type, duration) => {
            return this.toastManager.show(message, type, duration);
        };
        
        // Expose theme toggle
        window.toggleTheme = () => {
            return this.themeManager.toggleTheme();
        };
        
        // Expose sidebar controls
        window.openSidebar = () => this.sidebarManager.open();
        window.closeSidebar = () => this.sidebarManager.close();
        
        // Expose utility functions
        window.debounce = this.performanceManager.debounce;
        window.throttle = this.performanceManager.throttle;
    }
}

// ========== AUTO-INITIALIZATION ==========
const globalApp = new GlobalApp();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ThemeManager,
        SidebarManager,
        ToastManager,
        AccessibilityManager,
        PerformanceManager,
        GlobalApp
    };
}
