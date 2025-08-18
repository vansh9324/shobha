// ========== ENHANCED PHOTO MAKER UI (Mobile-First) ==========
class PhotoMakerUI {
    constructor() {
        // State management
        this.items = [];
        this.idSeq = 0;
        this.isProcessing = false;
        this.lastRenderedCount = 0;
        
        // Mobile-responsive settings
        this.updateViewportSettings();
        
        // Camera stream
        this.stream = null;
        
        // Performance tracking
        this.performanceMetrics = {
            compressionTime: 0,
            uploadTime: 0,
            totalFiles: 0
        };
        
        // DOM Elements cache
        this.elements = this.cacheElements();
        
        // Initialize the app
        this.init();
    }
    
    // ========== INITIALIZATION ==========
    cacheElements() {
        return {
            // Form elements
            fileInput: document.getElementById('fileInput'),
            dropzone: document.getElementById('dropzone'),
            form: document.getElementById('uploadForm'),
            processBtn: document.getElementById('processBtn'),
            catalogSelect: document.getElementById('catalog-select'),
            
            // Preview elements
            viewport: document.getElementById('previewViewport'),
            vgrid: document.getElementById('previewGrid'),
            spacer: document.getElementById('previewSpacer'),
            
            // Results elements
            resultsPanel: document.getElementById('resultsPanel'),
            resultsGrid: document.getElementById('resultsGrid'),
            
            // Progress elements
            progressContainer: document.getElementById('progressContainer'),
            progressFill: document.getElementById('progressFill'),
            progressPercentage: document.getElementById('progressPercentage'),
            progressStatus: document.getElementById('progressStatus'),
            
            // Camera elements
            cameraModal: document.getElementById('cameraModal'),
            cameraVideo: document.getElementById('cameraVideo'),
            cameraCanvas: document.getElementById('cameraCanvas'),
            openCameraBtn: document.getElementById('openCameraBtn'),
            captureBtn: document.getElementById('captureBtn'),
            closeCameraBtn: document.getElementById('closeCameraBtn'),
            
            // Navigation elements
            hamburger: document.getElementById('globalHamburger'),
            sidebar: document.getElementById('glassmorphicSidebar'),
            overlay: document.getElementById('sidebarOverlay'),
            themeSwitch: document.getElementById('themeSwitchGlobal'),
            navLogo: document.getElementById('navLogo'),
            sidebarLogo: document.getElementById('sidebarLogo'),
            appBg: document.getElementById('appLogoBg'),
            
            // Toast system
            toastHost: document.getElementById('toastHost')
        };
    }
    
    updateViewportSettings() {
        const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
        
        if (vw <= 480) {
            // Mobile settings
            this.cardW = 120;
            this.cardH = 160;
            this.gap = 8;
            this.colCount = 2;
        } else if (vw <= 768) {
            // Tablet settings
            this.cardW = 140;
            this.cardH = 170;
            this.gap = 10;
            this.colCount = 3;
        } else {
            // Desktop settings
            this.cardW = 160;
            this.cardH = 180;
            this.gap = 12;
            this.colCount = 4;
        }
    }
    
    init() {
        this.initTheme();
        this.initSidebar();
        this.initDropzone();
        this.initCamera();
        this.initForm();
        this.initVirtualization();
        this.bindEvents();
        
        // Mobile-specific initialization
        this.initMobileOptimizations();
        this.initTouchGestures();
        
        console.log('✅ PhotoMaker UI initialized');
    }
    
    initMobileOptimizations() {
        // Prevent bounce scrolling on iOS
        document.body.addEventListener('touchmove', (e) => {
            if (e.target === document.body) {
                e.preventDefault();
            }
        }, { passive: false });
        
        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.updateViewportSettings();
                this.updateLayout();
            }, 100);
        });
        
        // Handle resize for responsive updates
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.updateViewportSettings();
                this.updateLayout();
            }, 150);
        });
    }
    
    initTouchGestures() {
        // Add touch feedback to buttons
        const buttons = document.querySelectorAll('.btn-glass, .glassmorphic-btn, .nav-item');
        
        buttons.forEach(btn => {
            btn.addEventListener('touchstart', () => {
                btn.style.transform = 'scale(0.95)';
            }, { passive: true });
            
            btn.addEventListener('touchend', () => {
                setTimeout(() => {
                    btn.style.transform = '';
                }, 100);
            }, { passive: true });
        });
    }
    
    // ========== THEME MANAGEMENT ==========
    initTheme() {
        try {
            const saved = localStorage.getItem('theme');
            if (saved) document.documentElement.setAttribute('data-theme', saved);
        } catch(e) {
            console.warn('Could not access localStorage:', e);
        }
        
        if (!this.elements.themeSwitch) return;
        
        const updateTheme = (theme) => {
            const logoSrc = theme === 'light' ? '/static/logo-red.png' : '/static/logo.png';
            
            // Update all logos efficiently
            [this.elements.navLogo, this.elements.sidebarLogo].forEach(logo => {
                if (logo) logo.src = logoSrc;
            });
            
            if (this.elements.appBg) {
                this.elements.appBg.style.backgroundImage = `url("${logoSrc}")`;
            }
            
            this.elements.themeSwitch.setAttribute('aria-checked', theme === 'light' ? 'true' : 'false');
        };
        
        const toggle = () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            
            try {
                localStorage.setItem('theme', newTheme);
            } catch(e) {
                console.warn('Could not save to localStorage:', e);
            }
            
            updateTheme(newTheme);
            this.showToast(`Switched to ${newTheme} theme`, 'good');
        };
        
        // Bind events
        this.elements.themeSwitch.addEventListener('click', toggle);
        this.elements.themeSwitch.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggle();
            }
        });
        
        // Set initial theme
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        updateTheme(currentTheme);
    }
    
    // ========== SIDEBAR MANAGEMENT ==========
    initSidebar() {
        const { hamburger, sidebar, overlay } = this.elements;
        if (!hamburger || !sidebar || !overlay) return;
        
        const openSidebar = () => {
            sidebar.classList.add('active');
            overlay.classList.add('active');
            hamburger.classList.add('active');
            hamburger.setAttribute('aria-expanded', 'true');
            sidebar.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
            
            // Focus first focusable element in sidebar
            const firstFocusable = sidebar.querySelector('a, button');
            if (firstFocusable) firstFocusable.focus();
        };
        
        const closeSidebar = () => {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
            hamburger.classList.remove('active');
            hamburger.setAttribute('aria-expanded', 'false');
            sidebar.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            
            // Return focus to hamburger
            hamburger.focus();
        };
        
        const toggleSidebar = () => {
            if (sidebar.classList.contains('active')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        };
        
        // Bind events
        hamburger.addEventListener('click', toggleSidebar);
        overlay.addEventListener('click', closeSidebar);
        
        // Close on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && sidebar.classList.contains('active')) {
                closeSidebar();
            }
        });
        
        // Handle swipe gestures on mobile
        if ('ontouchstart' in window) {
            this.initSidebarSwipeGestures(sidebar, closeSidebar);
        }
    }
    
    initSidebarSwipeGestures(sidebar, closeSidebar) {
        let startX = 0;
        let startY = 0;
        
        sidebar.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches.clientY;
        }, { passive: true });
        
        sidebar.addEventListener('touchmove', (e) => {
            if (!startX || !startY) return;
            
            const diffX = startX - e.touches[0].clientX;
            const diffY = startY - e.touches.clientY;
            
            // Swipe left to close
            if (Math.abs(diffX) > Math.abs(diffY) && diffX > 50) {
                closeSidebar();
                startX = 0;
                startY = 0;
            }
        }, { passive: true });
    }
    
    // ========== ENHANCED DROPZONE ==========
    initDropzone() {
        const { dropzone, fileInput } = this.elements;
        if (!dropzone || !fileInput) return;
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        // Visual feedback
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => {
                dropzone.classList.add('drag');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => {
                dropzone.classList.remove('drag');
            });
        });
        
        // Handle drop
        dropzone.addEventListener('drop', (e) => {
            const files = Array.from(e.dataTransfer.files || []);
            if (files.length > 0) {
                this.addFiles(files);
            }
        });
        
        // Handle dropzone click
        dropzone.addEventListener('click', (e) => {
            if (e.target !== fileInput && !this.isProcessing) {
                e.preventDefault();
                fileInput.click();
            }
        });
        
        // Handle file input change
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files || []);
            if (files.length > 0) {
                this.addFiles(files);
            }
            e.target.value = ''; // Reset input
        });
    }
    
    // ========== ADVANCED FILE COMPRESSION ==========
    async compressImage(file, maxSizeMB = 3.5, quality = 0.85) {
        return new Promise((resolve, reject) => {
            const startTime = performance.now();
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                try {
                    let { width, height } = img;
                    
                    // Smart resizing based on file size and dimensions
                    const fileSizeMB = file.size / 1024 / 1024;
                    let maxDimension = 2400;
                    
                    if (fileSizeMB > 10) {
                        maxDimension = 2000;
                        quality = 0.8;
                    } else if (fileSizeMB > 5) {
                        maxDimension = 2200;
                        quality = 0.82;
                    }
                    
                    // Calculate new dimensions
                    if (width > maxDimension || height > maxDimension) {
                        const ratio = Math.min(maxDimension / width, maxDimension / height);
                        width = Math.round(width * ratio);
                        height = Math.round(height * ratio);
                    }
                    
                    canvas.width = width;
                    canvas.height = height;
                    
                    // Apply image smoothing for better quality
                    ctx.imageSmoothingEnabled = true;
                    ctx.imageSmoothingQuality = 'high';
                    
                    // Draw and compress
                    ctx.drawImage(img, 0, 0, width, height);
                    
                    // Convert to blob with progressive quality adjustment
                    let currentQuality = quality;
                    const tryCompress = () => {
                        canvas.toBlob((blob) => {
                            if (!blob) {
                                reject(new Error('Compression failed'));
                                return;
                            }
                            
                            const compressedSizeMB = blob.size / 1024 / 1024;
                            
                            // If still too large, reduce quality
                            if (compressedSizeMB > maxSizeMB && currentQuality > 0.6) {
                                currentQuality -= 0.05;
                                tryCompress();
                                return;
                            }
                            
                            const compressedFile = new File(
                                [blob],
                                file.name.replace(/\.[^/.]+$/, '.jpg'),
                                { type: 'image/jpeg', lastModified: Date.now() }
                            );
                            
                            const endTime = performance.now();
                            this.performanceMetrics.compressionTime += endTime - startTime;
                            
                            console.log(`✅ Compressed ${file.name}: ${fileSizeMB.toFixed(2)}MB → ${compressedSizeMB.toFixed(2)}MB (${((1 - compressedSizeMB/fileSizeMB) * 100).toFixed(1)}% reduction)`);
                            
                            resolve(compressedFile);
                        }, 'image/jpeg', currentQuality);
                    };
                    
                    tryCompress();
                    
                } catch (error) {
                    reject(error);
                }
            };
            
            img.onerror = () => reject(new Error('Failed to load image'));
            img.src = URL.createObjectURL(file);
        });
    }
    
    // ========== ENHANCED FILE MANAGEMENT ==========
    async addFiles(files) {
        const imageFiles = files.filter(f => f && f.type && f.type.startsWith('image/'));
        
        if (!imageFiles.length) {
            this.showToast('No valid images selected', 'info');
            return;
        }
        
        if (this.items.length + imageFiles.length > 10) {
            this.showToast(`Maximum 10 files allowed. Currently have ${this.items.length}`, 'bad');
            return;
        }
        
        this.showToast(`Processing ${imageFiles.length} image${imageFiles.length > 1 ? 's' : ''}...`, 'info');
        
        const processedFiles = [];
        let compressionCount = 0;
        
        for (const file of imageFiles) {
            try {
                let processedFile = file;
                const fileSizeMB = file.size / 1024 / 1024;
                
                // Compress files larger than 2.5MB
                if (fileSizeMB > 2.5) {
                    this.showToast(`Compressing ${file.name} (${fileSizeMB.toFixed(1)}MB)...`, 'info');
                    processedFile = await this.compressImage(file, 3.5, 0.85);
                    compressionCount++;
                }
                
                processedFiles.push(processedFile);
                
            } catch (error) {
                console.error(`Error processing ${file.name}:`, error);
                this.showToast(`Failed to process ${file.name}`, 'bad');
            }
        }
        
        // Filter out duplicates
        const uniqueFiles = this.dedupeFiles(processedFiles);
        
        if (!uniqueFiles.length) {
            this.showToast('No new images to add', 'info');
            return;
        }
        
        // Add to items
        uniqueFiles.forEach(file => {
            this.items.push({
                file,
                id: this.idSeq++,
                design: '',
                url: URL.createObjectURL(file),
                originalSize: files.find(f => f.name === file.name.replace('.jpg', ''))?.size || file.size,
                compressed: file.type === 'image/jpeg' && compressionCount > 0
            });
        });
        
        const message = compressionCount > 0 
            ? `Added ${uniqueFiles.length} image${uniqueFiles.length > 1 ? 's' : ''} (${compressionCount} compressed)`
            : `Added ${uniqueFiles.length} image${uniqueFiles.length > 1 ? 's' : ''}`;
            
        this.showToast(message, 'good');
        this.updateLayout();
        
        // Update performance metrics
        this.performanceMetrics.totalFiles += uniqueFiles.length;
    }
    
    dedupeFiles(files) {
        const existing = new Set(
            this.items.map(item => `${item.file.name}|${item.file.size}`)
        );
        return files.filter(f => !existing.has(`${f.name}|${f.size}`));
    }
    
    clearAll() {
        // Show confirmation on mobile
        if (this.items.length > 0) {
            const isMobile = window.innerWidth <= 768;
            if (isMobile && !confirm(`Clear all ${this.items.length} images?`)) {
                return;
            }
        }
        
        // Revoke blob URLs to free memory
        this.items.forEach(item => {
            if (item.url) URL.revokeObjectURL(item.url);
        });
        
        this.items = [];
        this.lastRenderedCount = 0;
        this.performanceMetrics = { compressionTime: 0, uploadTime: 0, totalFiles: 0 };
        
        if (this.elements.vgrid) this.elements.vgrid.innerHTML = '';
        if (this.elements.spacer) this.elements.spacer.style.height = '0px';
        
        this.showToast('All images cleared', 'info');
    }
    
    // Continue with remaining methods...
    // (I'll provide the rest when you ask for the next part)
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.photoMakerUI = new PhotoMakerUI();
});

// Export for global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PhotoMakerUI;
}
