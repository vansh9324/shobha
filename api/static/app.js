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
    // ========== CAMERA MANAGEMENT (MOBILE OPTIMIZED) ==========
    initCamera() {
        const { openCameraBtn, captureBtn, closeCameraBtn } = this.elements;
        
        if (openCameraBtn) {
            openCameraBtn.addEventListener('click', () => this.openCamera());
        }
        if (captureBtn) {
            captureBtn.addEventListener('click', () => this.captureFromCamera());
        }
        if (closeCameraBtn) {
            closeCameraBtn.addEventListener('click', () => this.closeCamera());
        }
    }

    async openCamera() {
        try {
            // Check for camera permissions first
            const permissions = await navigator.permissions.query({ name: 'camera' });
            if (permissions.state === 'denied') {
                this.showToast('Camera permission denied. Please enable in settings.', 'bad');
                return;
            }

            // Request camera with mobile-optimized constraints
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 1920, max: 3840 },
                    height: { ideal: 1080, max: 2160 }
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.elements.cameraVideo.srcObject = this.stream;
            this.elements.cameraModal.classList.add('show');
            
            // Focus management
            this.elements.captureBtn.focus();
            
            this.showToast('Camera ready! Position your saree and tap capture', 'good');
            
        } catch (error) {
            console.error('Camera error:', error);
            let message = 'Camera not available';
            
            if (error.name === 'NotAllowedError') {
                message = 'Camera permission denied. Please allow camera access.';
            } else if (error.name === 'NotFoundError') {
                message = 'No camera found on this device.';
            } else if (error.name === 'NotSupportedError') {
                message = 'Camera not supported in this browser.';
            }
            
            this.showToast(message, 'bad');
        }
    }

    async captureFromCamera() {
        if (!this.stream) return;

        const { cameraVideo, cameraCanvas } = this.elements;
        const w = cameraVideo.videoWidth;
        const h = cameraVideo.videoHeight;

        if (!w || !h) {
            this.showToast('Camera not ready. Please wait...', 'bad');
            return;
        }

        cameraCanvas.width = w;
        cameraCanvas.height = h;

        const ctx = cameraCanvas.getContext('2d');
        ctx.drawImage(cameraVideo, 0, 0, w, h);

        try {
            const blob = await new Promise(resolve => 
                cameraCanvas.toBlob(resolve, 'image/jpeg', 0.92)
            );
            
            if (!blob) {
                this.showToast('Failed to capture image', 'bad');
                return;
            }

            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            let file = new File([blob], `camera-capture-${timestamp}.jpg`, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });

            // Compress if needed
            const fileSizeMB = file.size / 1024 / 1024;
            if (fileSizeMB > 3) {
                this.showToast('Compressing captured image...', 'info');
                file = await this.compressImage(file, 3.5, 0.85);
            }

            this.addFiles([file]);
            this.closeCamera();
            
        } catch (error) {
            console.error('Capture error:', error);
            this.showToast('Failed to capture image', 'bad');
        }
    }

    closeCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        this.elements.cameraModal.classList.remove('show');
        
        // Return focus to camera button
        if (this.elements.openCameraBtn) {
            this.elements.openCameraBtn.focus();
        }
    }

    // ========== FORM MANAGEMENT (ENHANCED) ==========
    initForm() {
        if (this.elements.form) {
            this.elements.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        const clearBtn = document.getElementById('clearAllBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearAll());
        }

        // Auto-save form state
        if (this.elements.catalogSelect) {
            this.elements.catalogSelect.addEventListener('change', () => {
                this.saveFormState();
            });
        }

        // Load saved form state
        this.loadFormState();
    }

    saveFormState() {
        try {
            const state = {
                catalog: this.elements.catalogSelect?.value || '',
                designs: this.items.map(item => item.design)
            };
            localStorage.setItem('photomaker_form_state', JSON.stringify(state));
        } catch (e) {
            console.warn('Could not save form state:', e);
        }
    }

    loadFormState() {
        try {
            const saved = localStorage.getItem('photomaker_form_state');
            if (saved) {
                const state = JSON.parse(saved);
                if (this.elements.catalogSelect && state.catalog) {
                    this.elements.catalogSelect.value = state.catalog;
                }
            }
        } catch (e) {
            console.warn('Could not load form state:', e);
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        if (this.isProcessing) {
            this.showToast('Upload already in progress...', 'info');
            return;
        }

        // Validation
        if (!this.items.length) {
            this.showToast('No images to process', 'bad');
            return;
        }

        if (!this.elements.catalogSelect?.value) {
            this.showToast('Please select a catalog', 'bad');
            this.elements.catalogSelect?.focus();
            return;
        }

        // Check total file size
        const totalSize = this.items.reduce((sum, item) => sum + item.file.size, 0);
        const totalSizeMB = totalSize / 1024 / 1024;
        
        if (totalSizeMB > 15) {
            this.showToast(`Total size (${totalSizeMB.toFixed(1)}MB) exceeds 15MB limit`, 'bad');
            return;
        }

        this.isProcessing = true;
        const uploadStartTime = performance.now();

        try {
            const formData = new FormData();
            formData.append('catalog', this.elements.catalogSelect.value);

            // Create mapping with validation
            const mapping = this.items.map((item, index) => {
                const designNumber = item.design?.trim() || `Design_${index + 1}`;
                return { index, design_number: designNumber };
            });
            
            formData.append('mapping', JSON.stringify(mapping));

            // Append files
            this.items.forEach(item => {
                formData.append('files', item.file);
            });

            this.showProgress();

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                const uploadEndTime = performance.now();
                this.performanceMetrics.uploadTime = uploadEndTime - uploadStartTime;
                
                this.displayResults(data);
                this.showPerformanceStats();
                
                const successCount = data.results.filter(r => r.status === 'success').length;
                const errorCount = data.results.filter(r => r.status === 'error').length;
                
                if (successCount > 0) {
                    this.showToast(
                        `Successfully processed ${successCount} of ${data.results.length} images`, 
                        'good'
                    );
                }
                
                if (errorCount > 0) {
                    this.showToast(
                        `${errorCount} images failed to process`, 
                        'bad'
                    );
                }

                // Clear form after successful upload
                if (successCount === data.results.length) {
                    setTimeout(() => {
                        this.clearAll();
                        this.elements.catalogSelect.selectedIndex = 0;
                    }, 2000);
                }

            } else {
                // Handle different error types
                if (response.status === 401) {
                    this.showToast('Session expired. Redirecting to login...', 'bad');
                    setTimeout(() => window.location.href = '/login', 2000);
                } else if (response.status === 413) {
                    this.showToast('Files too large. Please compress or reduce file count.', 'bad');
                } else if (response.status === 503) {
                    this.showToast('Service temporarily unavailable. Please try again.', 'bad');
                } else {
                    this.showToast(data.error || 'Upload failed. Please try again.', 'bad');
                }
            }

        } catch (error) {
            console.error('Upload error:', error);
            
            if (error.name === 'TypeError' || error.message.includes('fetch')) {
                this.showToast('Network error. Check your connection and try again.', 'bad');
            } else {
                this.showToast('Upload failed. Please try again.', 'bad');
            }

        } finally {
            this.isProcessing = false;
            this.hideProgress();
            this.saveFormState();
        }
    }

    showPerformanceStats() {
        const { compressionTime, uploadTime, totalFiles } = this.performanceMetrics;
        
        if (totalFiles > 0) {
            console.log(`📊 Performance Stats:
                Files: ${totalFiles}
                Compression: ${(compressionTime / 1000).toFixed(2)}s
                Upload: ${(uploadTime / 1000).toFixed(2)}s
                Avg compression: ${(compressionTime / totalFiles / 1000).toFixed(2)}s per file`
            );
        }
    }

    // ========== VIRTUALIZATION (MOBILE OPTIMIZED) ==========
    initVirtualization() {
        if (this.elements.viewport) {
            this.computeColumns();
            
            // Debounced resize handler
            let resizeTimeout;
            window.addEventListener('resize', () => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => this.onResize(), 150);
            });

            // Optimized scroll handling
            this.elements.viewport.addEventListener('scroll', 
                this.throttle(() => this.updateVisibleCards(), 16), 
                { passive: true }
            );
        }
    }

    computeColumns() {
        if (!this.elements.viewport) return;
        
        const vpW = this.elements.viewport.clientWidth || 320;
        const availableWidth = vpW - (this.gap * 2);
        const cardPlusGap = this.cardW + this.gap;
        
        this.colCount = Math.max(1, Math.floor(availableWidth / cardPlusGap));
        
        // Adjust card width to fill available space better on mobile
        if (window.innerWidth <= 480 && this.colCount === 2) {
            const remainingSpace = availableWidth - (this.colCount * cardPlusGap);
            if (remainingSpace > 10) {
                this.cardW += Math.floor(remainingSpace / this.colCount);
            }
        }
    }

    onResize() {
        const prevCols = this.colCount;
        this.updateViewportSettings();
        this.computeColumns();
        
        if (prevCols !== this.colCount) {
            this.updateLayout();
        }
    }

    updateLayout() {
        const { spacer, vgrid } = this.elements;
        if (!spacer || !vgrid) return;

        if (this.items.length === 0) {
            spacer.style.height = '0px';
            vgrid.innerHTML = '';
            this.lastRenderedCount = 0;
            return;
        }

        this.computeColumns();
        this.rowCount = Math.ceil(this.items.length / this.colCount);
        const totalHeight = this.rowCount * (this.cardH + this.gap) + this.gap;
        spacer.style.height = `${totalHeight}px`;

        // Clear and re-render if column count changed
        const mustRelayout = this.lastRenderedCount > this.items.length || 
                           vgrid.children.length !== this.items.length;
        
        if (mustRelayout) {
            vgrid.innerHTML = '';
            this.lastRenderedCount = 0;
        }

        this.renderItems();
    }

    renderItems() {
        const { vgrid } = this.elements;
        if (!vgrid) return;

        const start = this.lastRenderedCount || 0;
        const total = this.items.length;
        
        if (start >= total) return;

        // Batch rendering for performance
        const batch = window.innerWidth <= 768 ? 20 : 40;
        let i = start;

        const renderBatch = () => {
            const frag = document.createDocumentFragment();
            const end = Math.min(i + batch, total);

            for (; i < end; i++) {
                const r = Math.floor(i / this.colCount);
                const c = i % this.colCount;
                const x = this.gap + c * (this.cardW + this.gap);
                const y = this.gap + r * (this.cardH + this.gap);
                
                frag.appendChild(this.createCard(this.items[i], x, y));
            }

            vgrid.appendChild(frag);

            if (i < total) {
                requestAnimationFrame(renderBatch);
            } else {
                this.lastRenderedCount = total;
            }
        };

        requestAnimationFrame(renderBatch);
    }

    createCard(item, x, y) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.width = `${this.cardW}px`;
        card.style.transform = `translate(${x}px, ${y}px)`;
        card.style.position = 'absolute';
        card.setAttribute('role', 'article');
        card.setAttribute('aria-label', `Image: ${item.file.name}`);

        // Image with loading optimization
        const img = document.createElement('img');
        img.className = 'thumb';
        img.loading = 'lazy';
        img.decoding = 'async';
        img.width = this.cardW;
        img.height = Math.round(this.cardH * 0.67); // Maintain aspect ratio
        img.src = item.url;
        img.alt = `Preview of ${item.file.name}`;
        
        // Add compression indicator
        if (item.compressed) {
            img.title = `Compressed image (Original: ${(item.originalSize / 1024 / 1024).toFixed(1)}MB)`;
        }

        // Card body
        const body = document.createElement('div');
        body.className = 'card-body';

        // Accessible label
        const label = document.createElement('label');
        label.className = 'sr-only';
        label.textContent = `Design number for ${item.file.name}`;
        label.setAttribute('for', `design-input-${item.id}`);

        // Input field
        const input = document.createElement('input');
        input.id = `design-input-${item.id}`;
        input.className = 'input';
        input.placeholder = 'Design Number';
        input.value = item.design || '';
        input.inputMode = 'numeric';
        input.setAttribute('aria-label', `Design number for ${item.file.name}`);
        
        // Enhanced input handling
        input.addEventListener('input', this.debounce((e) => {
            item.design = e.target.value.trim();
            this.saveFormState();
        }, 300));

        // Mobile keyboard optimization
        if ('ontouchstart' in window) {
            input.addEventListener('focus', () => {
                // Scroll card into view on mobile
                setTimeout(() => {
                    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 300);
            });
        }

        body.appendChild(label);
        body.appendChild(input);
        card.appendChild(img);
        card.appendChild(body);

        return card;
    }

    updateVisibleCards() {
        // Optimized visible card updates for scroll performance
        // Implementation for lazy loading improvements
        const viewport = this.elements.viewport;
        if (!viewport) return;

        const scrollTop = viewport.scrollTop;
        const viewportHeight = viewport.clientHeight;
        const cards = viewport.querySelectorAll('.card img[loading="lazy"]');

        cards.forEach(img => {
            const rect = img.getBoundingClientRect();
            if (rect.top < viewportHeight + 100 && rect.bottom > -100) {
                img.loading = 'eager';
            }
        });
    }

    // ========== PROGRESS BAR (ENHANCED) ==========
    showProgress() {
        const { progressContainer, processBtn } = this.elements;
        if (progressContainer && processBtn) {
            processBtn.style.display = 'none';
            progressContainer.style.display = 'block';
            this.animateProgress();
        }
    }

    hideProgress() {
        const { progressContainer, processBtn } = this.elements;
        if (progressContainer && processBtn) {
            setTimeout(() => {
                progressContainer.style.display = 'none';
                processBtn.style.display = 'flex';
            }, 1000);
        }
    }

    animateProgress() {
        const { progressFill, progressPercentage, progressStatus } = this.elements;
        if (!progressFill || !progressPercentage || !progressStatus) return;

        let progress = 0;
        const stages = [
            { end: 15, text: '📋 Validating files...', duration: 500 },
            { end: 35, text: '🎭 Removing backgrounds...', duration: 2000 },
            { end: 55, text: '🎨 Processing images...', duration: 1500 },
            { end: 75, text: '🏷️ Adding branding...', duration: 1000 },
            { end: 90, text: '☁️ Uploading to drive...', duration: 2000 },
            { end: 100, text: '✅ Complete!', duration: 500 }
        ];

        let currentStage = 0;
        let stageStartTime = Date.now();

        const updateProgress = () => {
            if (!this.isProcessing) return;

            if (currentStage < stages.length) {
                const stage = stages[currentStage];
                const elapsed = Date.now() - stageStartTime;
                const stageProgress = Math.min(elapsed / stage.duration, 1);
                
                const stageStart = currentStage === 0 ? 0 : stages[currentStage - 1].end;
                progress = stageStart + (stage.end - stageStart) * stageProgress;

                progressStatus.textContent = stage.text;
                progressFill.style.width = `${progress}%`;
                progressPercentage.textContent = `${Math.round(progress)}%`;

                if (stageProgress >= 1 && currentStage < stages.length - 1) {
                    currentStage++;
                    stageStartTime = Date.now();
                }

                if (progress < 100) {
                    requestAnimationFrame(updateProgress);
                } else {
                    setTimeout(() => this.hideProgress(), 1500);
                }
            }
        };

        requestAnimationFrame(updateProgress);
    }

    // ========== RESULTS MANAGEMENT ==========
    displayResults(data) {
        if (!this.elements.resultsGrid) return;

        this.elements.resultsGrid.innerHTML = '';
        
        if (!data.results || data.results.length === 0) {
            this.elements.resultsGrid.innerHTML = '<p class="text-center text-muted">No results to display</p>';
            return;
        }

        data.results.forEach((result, index) => {
            const div = document.createElement('div');
            div.className = 'result';
            div.setAttribute('role', 'listitem');
            
            const statusIcon = result.status === 'success' ? '✅' : '❌';
            const statusClass = result.status === 'success' ? 'ok' : 'err';
            
            div.innerHTML = `
                <div class="result-head">
                    <div class="status ${statusClass}" aria-label="${result.status}"></div>
                    <div class="result-name">${result.filename}</div>
                </div>
                ${result.status === 'success' && result.url ? 
                    `<a href="${result.url}" target="_blank" rel="noopener" class="link" aria-label="Open ${result.filename} in Google Drive">View in Drive →</a>` :
                    `<div class="error-text" style="color: var(--bad); font-size: 0.8125rem; margin-top: 4px;">${result.error || 'Processing failed'}</div>`
                }
                ${result.design_number ? `<div style="font-size: 0.75rem; color: var(--muted); margin-top: 4px;">Design: ${result.design_number}</div>` : ''}
            `;
            
            this.elements.resultsGrid.appendChild(div);
        });

        // Show results panel with animation
        if (this.elements.resultsPanel) {
            this.elements.resultsPanel.style.display = 'block';
            this.elements.resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // ========== UTILITY FUNCTIONS ==========
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

    showToast(message, type = 'info') {
        const toastHost = this.elements.toastHost || this.createToastHost();
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        const icons = { good: '✅', bad: '❌', info: 'ℹ️', warning: '⚠️' };
        
        toast.innerHTML = `
            <span class="toast-icon" aria-hidden="true">${icons[type] || 'ℹ️'}</span>
            <span class="toast-message">${message}</span>
        `;

        toastHost.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));

        // Auto remove after delay
        const delay = type === 'bad' ? 5000 : 3000;
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, delay);

        // Remove on click
        toast.addEventListener('click', () => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        });
    }

    createToastHost() {
        const host = document.createElement('div');
        host.id = 'toastHost';
        host.className = 'toast-host';
        document.body.appendChild(host);
        this.elements.toastHost = host;
        return host;
    }

    // ========== CLEANUP ==========
    destroy() {
        // Clean up resources
        this.items.forEach(item => {
            if (item.url) URL.revokeObjectURL(item.url);
        });
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        
        // Remove event listeners
        window.removeEventListener('resize', this.onResize);
        window.removeEventListener('orientationchange', this.updateViewportSettings);
        
        console.log('PhotoMakerUI destroyed');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.photoMakerUI = new PhotoMakerUI();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.photoMakerUI) {
        window.photoMakerUI.destroy();
    }
});

// Export for global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PhotoMakerUI;
}
