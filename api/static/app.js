// ========== OPTIMIZED PHOTO MAKER UI ==========
class PhotoMakerUI {
  // Track last rendered count to append only new cards
  _lastRenderedCount = 0;

  constructor() {
    // State management
    this.items = [];
    this.idSeq = 0;
    this.isProcessing = false;
    
    // DOM Elements - cached for performance
    this.elements = this.cacheElements();
    
    // Virtualization settings
    this.cardW = 160;
    this.cardH = 180; // 120 + 8 + 40 + 12
    this.gap = 10;
    this.colCount = 2;
    this.rowCount = 0;
    
    // Camera stream
    this.stream = null;
    
    // Initialize the app
    this.init();
  }
  
  // Cache all DOM elements for better performance
  cacheElements() {
    return {
      // Form elements
      fileInput: document.getElementById('fileInput'),
      dropzone: document.getElementById('dropzone'),
      form: document.getElementById('uploadForm'),
      processBtn: document.getElementById('processBtn'),
      
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
      
      // Toast
      toastHost: document.getElementById('toastHost')
    };
  }
  
  // Initialize all functionality
  init() {
    this.initTheme();
    this.initSidebar();
    this.initDropzone();
    this.initCamera();
    this.initForm();
    this.initVirtualization();
    this.bindEvents();
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
    
    // Bind events
    hamburger.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', closeSidebar);
    
    // Close on escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeSidebar();
    });
  }
  
  // ========== DROPZONE MANAGEMENT ==========
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
      this.addFiles(files);
    });
    
    // Handle file input
    fileInput.addEventListener('change', (e) => {
      const files = Array.from(e.target.files || []);
      this.addFiles(files);
      e.target.value = ''; // Reset input
    });
  }
  
  // ========== CAMERA MANAGEMENT ==========
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
      this.stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: { ideal: 'environment' } }, 
        audio: false 
      });
      this.elements.cameraVideo.srcObject = this.stream;
      this.elements.cameraModal.classList.add('show');
    } catch(e) {
      this.showToast('Camera not available', 'bad');
      console.error('Camera error:', e);
    }
  }
  
  async captureFromCamera() {
    if (!this.stream) return;
    const { cameraVideo, cameraCanvas } = this.elements;
    
    const w = cameraVideo.videoWidth;
    const h = cameraVideo.videoHeight;
    if (!w || !h) return;
    
    cameraCanvas.width = w;
    cameraCanvas.height = h;
    
    const ctx = cameraCanvas.getContext('2d');
    ctx.drawImage(cameraVideo, 0, 0, w, h);
    
    try {
      const blob = await new Promise(resolve => 
        cameraCanvas.toBlob(resolve, 'image/jpeg', 0.92)
      );
      
      if (!blob) return;
      
      let file = new File([blob], `capture_${Date.now()}.jpg`, { 
        type: 'image/jpeg', 
        lastModified: Date.now() 
      });
      
      // Compress if needed
      if (file.size > 10 * 1024 * 1024) {
        file = await this.compressFile(file, 10 * 1024 * 1024);
      }
      
      this.addFiles([file]);
      this.closeCamera();
    } catch(e) {
      this.showToast('Failed to capture image', 'bad');
      console.error('Capture error:', e);
    }
  }
  
  closeCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.elements.cameraModal.classList.remove('show');
  }
  
  // ========== FORM MANAGEMENT ==========
  initForm() {
    if (this.elements.form) {
      this.elements.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }
    
    const clearBtn = document.getElementById('clearAllBtn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearAll());
    }
  }
  
  async handleSubmit(e) {
    e.preventDefault();
    
    if (this.isProcessing) return;
    if (!this.items.length) {
      this.showToast('No images to process', 'bad');
      return;
    }
    
    const catalogSelect = this.elements.form.querySelector('select[name="catalog"]');
    if (!catalogSelect.value) {
      this.showToast('Please select a catalog', 'bad');
      return;
    }
    
    this.isProcessing = true;
    
    try {
      const formData = new FormData();
      formData.append('catalog', catalogSelect.value);
      
      const mapping = this.items.map((item, index) => ({
        index,
        design_number: item.design || `Design_${index + 1}`
      }));
      formData.append('mapping', JSON.stringify(mapping));
      
      this.items.forEach(item => formData.append('files', item.file));
      
      this.showProgress();
      
      const response = await fetch('/upload', { 
        method: 'POST', 
        body: formData 
      });
      
      const data = await response.json();
      
      if (response.ok) {
        this.displayResults(data);
        const successCount = data.results.filter(r => r.status === 'success').length;
        this.showToast(`Successfully processed ${successCount} images`, 'good');
      } else {
        this.showToast(data.error || 'Upload failed', 'bad');
      }
    } catch(error) {
      this.showToast('Network error occurred', 'bad');
      console.error('Upload error:', error);
    } finally {
      this.isProcessing = false;
      // Progress bar will hide automatically
    }
  }
  
  // ========== FILE MANAGEMENT ==========
  addFiles(files) {
    const validFiles = files.filter(f => f && f.type && f.type.startsWith('image/'));
    const uniqueFiles = this.dedupeFiles(validFiles);
    if (!uniqueFiles.length) {
      this.showToast('No new images added', 'info');
      return;
    }
    // Create blob URL once per file
    uniqueFiles.forEach(file => {
      this.items.push({
        file,
        id: this.idSeq++,
        design: '',
        url: URL.createObjectURL(file)
      });
    });
    this.showToast(`Added ${uniqueFiles.length} image${uniqueFiles.length > 1 ? 's' : ''}`, 'good');
    this.updateLayout();
  }
  
  dedupeFiles(files) {
    const existing = new Set(
      this.items.map(item => `${item.file.name}|${item.file.size}|${item.file.lastModified}`)
    );
    return files.filter(f => !existing.has(`${f.name}|${f.size}|${f.lastModified}`));
  }
  
  clearAll() {
    // Revoke blob URLs to free memory and prevent churn
    this.items.forEach(item => {
      if (item.url) URL.revokeObjectURL(item.url);
    });
    this.items = [];
    this._lastRenderedCount = 0;
    if (this.elements.vgrid) this.elements.vgrid.innerHTML = '';
    if (this.elements.spacer) this.elements.spacer.style.height = '0px';
    this.showToast('All images cleared', 'info');
  }
  
  // ========== VIRTUALIZATION ==========
  initVirtualization() {
    if (this.elements.viewport) {
      this.computeColumns();
      window.addEventListener('resize', this.debounce(() => this.onResize(), 100));
    }
  }
  
  computeColumns() {
    if (!this.elements.viewport) return;
    const vpW = this.elements.viewport.clientWidth || 320;
    this.colCount = Math.max(1, Math.floor((vpW + this.gap) / (this.cardW + this.gap)));
  }
  
  onResize() {
    const prevCols = this.colCount;
    this.computeColumns();
    if (prevCols !== this.colCount) {
      this.updateLayout();
    }
  }
  
  updateLayout() {
    const { spacer, vgrid } = this.elements;
    if (!spacer || !vgrid) return;

    // Recompute columns only if needed
    const prevCols = this.colCount;
    this.computeColumns();

    // If column count changed, we must reposition all cards
    const mustRelayout = prevCols !== this.colCount;

    if (this.items.length === 0) {
      spacer.style.height = '0px';
      vgrid.innerHTML = '';
      this._lastRenderedCount = 0;
      return;
    }

    this.rowCount = Math.ceil(this.items.length / this.colCount);
    const totalHeight = this.rowCount * (this.cardH + this.gap) + this.gap;
    spacer.style.height = `${totalHeight}px`;

    if (mustRelayout) {
      // Reposition existing cards without recreating URLs
      vgrid.innerHTML = '';
      this._lastRenderedCount = 0;
    }

    // Append only the new items not yet rendered
    this.renderItems();
  }

  // Only append new cards; avoid clearing the grid
  renderItems() {
    const { vgrid } = this.elements;
    if (!vgrid) return;

    const start = this._lastRenderedCount || 0;
    const total = this.items.length;
    if (start >= total) return;

    const batch = 80; // tweak for device
    let i = start;

    const step = () => {
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
        requestAnimationFrame(step);
      } else {
        this._lastRenderedCount = total;
      }
    };
    requestAnimationFrame(step);
  }

  // Reuse the URL; set stable sizing hints
  createCard(item, x, y) {
    const card = document.createElement('div');
    card.className = 'card';
    card.style.width = `${this.cardW}px`;
    card.style.transform = `translate(${x}px, ${y}px)`;
    card.style.position = 'absolute';

    const img = document.createElement('img');
    img.className = 'thumb';
    img.loading = 'lazy';
    img.decoding = 'async';
    img.fetchPriority = 'low';
    img.width = this.cardW; // sizing hint to prevent reflow
    img.height = 120; // your fixed thumb height
    img.src = item.url; // reuse, do not recreate
    img.alt = item.file.name;
    img.style.contentVisibility = 'auto'; // reduces paint until visible

    const body = document.createElement('div');
    body.className = 'card-body';

    const input = document.createElement('input');
    input.className = 'input';
    input.placeholder = 'Design Number';
    input.value = item.design || '';
    input.inputMode = 'numeric';
    input.addEventListener('input', (e) => {
      item.design = e.target.value.trim();
    });

    body.appendChild(input);
    card.appendChild(img);
    card.appendChild(body);
    return card;
  }
  
  // ========== PROGRESS MANAGEMENT ==========
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
        processBtn.style.display = 'block';
      }, 1000);
    }
  }
  
  animateProgress() {
    const { progressFill, progressPercentage, progressStatus } = this.elements;
    if (!progressFill || !progressPercentage || !progressStatus) return;
    
    let progress = 0;
    const stages = [
      { end: 20, text: 'Validating images...' },
      { end: 40, text: 'Optimizing quality...' },
      { end: 65, text: 'Applying branding...' },
      { end: 85, text: 'Uploading to Drive...' },
      { end: 100, text: 'Complete!' }
    ];
    
    let currentStage = 0;
    
    const updateProgress = () => {
      if (currentStage < stages.length) {
        const stage = stages[currentStage];
        progressStatus.textContent = stage.text;
        
        const increment = Math.random() * 3 + 1;
        progress = Math.min(progress + increment, stage.end);
        
        progressFill.style.width = `${progress}%`;
        progressPercentage.textContent = `${Math.round(progress)}%`;
        
        if (progress >= stage.end) {
          currentStage++;
        }
        
        if (progress < 100) {
          setTimeout(updateProgress, 200 + Math.random() * 300);
        } else {
          setTimeout(() => this.hideProgress(), 1500);
        }
      }
    };
    
    updateProgress();
  }
  
  // ========== RESULTS MANAGEMENT ==========
  displayResults(data) {
    if (!this.elements.resultsGrid) return;
    
    this.elements.resultsGrid.innerHTML = '';
    
    data.results.forEach(result => {
      const div = document.createElement('div');
      div.className = 'result';
      div.innerHTML = `
        <div class="result-head">
          <div class="status ${result.status === 'success' ? 'ok' : 'err'}"></div>
          <div class="result-name">${result.filename}</div>
        </div>
        ${result.status === 'success' 
          ? `<a href="${result.url}" target="_blank" class="link">View on Drive</a>`
          : `<div style="color: var(--bad); font-size: 13px;">${result.error}</div>`
        }
      `;
      this.elements.resultsGrid.appendChild(div);
    });
    
    this.elements.resultsPanel.style.display = 'block';
  }
  
  // ========== TOAST SYSTEM ==========
  showToast(message, type = 'info') {
    if (!this.elements.toastHost) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${type === 'good' ? '✅' : type === 'bad' ? '❌' : 'ℹ️'}</span>
      <span class="toast-message">${message}</span>
    `;
    
    this.elements.toastHost.appendChild(toast);
    
    // Show toast
    requestAnimationFrame(() => toast.classList.add('show'));
    
    // Auto remove
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove();
        }
      }, 300);
    }, 3000);
  }
  
  // ========== FILE COMPRESSION ==========
  async compressFile(file, maxBytes = 10 * 1024 * 1024) {
    try {
      const bitmap = await createImageBitmap(file);
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      // Calculate optimal size
      let { width, height } = bitmap;
      const maxDim = 2048;
      
      if (Math.max(width, height) > maxDim) {
        const scale = maxDim / Math.max(width, height);
        width = Math.round(width * scale);
        height = Math.round(height * scale);
      }
      
      canvas.width = width;
      canvas.height = height;
      ctx.drawImage(bitmap, 0, 0, width, height);
      
      // Try different quality levels
      for (const quality of [0.8, 0.6, 0.4, 0.2]) {
        const blob = await new Promise(resolve => 
          canvas.toBlob(resolve, 'image/jpeg', quality)
        );
        
        if (blob.size <= maxBytes) {
          return new File([blob], file.name.replace(/\.\w+$/, '.jpg'), {
            type: 'image/jpeg',
            lastModified: Date.now()
          });
        }
      }
      
      // If still too large, return heavily compressed version
      const blob = await new Promise(resolve => 
        canvas.toBlob(resolve, 'image/jpeg', 0.1)
      );
      
      return new File([blob], file.name.replace(/\.\w+$/, '.jpg'), {
        type: 'image/jpeg',
        lastModified: Date.now()
      });
    } catch(e) {
      console.error('Compression failed:', e);
      return file; // Return original if compression fails
    }
  }
  
  // ========== UTILITY FUNCTIONS ==========
  bindEvents() {
    // Handle window unload to clean up resources
    window.addEventListener('beforeunload', () => {
      this.cleanup();
    });
  }
  
  cleanup() {
    // Clean up camera stream
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
    
    // Clean up object URLs
    this.items.forEach(item => {
      if (item.url) URL.revokeObjectURL(item.url);
    });
  }
  
  // Debounce utility for performance
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

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new PhotoMakerUI();
});
