// ========== PHOTO MAKER UI (UPDATED FOR JWT BACKEND) ==========

class PhotoMakerUI {
    constructor() {
        this.items = [];
        this.idSeq = 0;
        this.isProcessing = false;
        this.stream = null;
        
        // Mobile-responsive settings
        this.cardW = window.innerWidth <= 768 ? 140 : 160;
        this.cardH = 180;
        this.gap = 12;
        this.colCount = Math.floor((window.innerWidth - 100) / (this.cardW + this.gap)) || 2;
        
        this.elements = this.cacheElements();
        this.init();
    }

    cacheElements() {
        return {
            fileInput: document.getElementById('fileInput'),
            dropzone: document.getElementById('dropzone'),
            form: document.getElementById('uploadForm'),
            processBtn: document.getElementById('processBtn'),
            catalogSelect: document.getElementById('catalog-select'),
            viewport: document.getElementById('previewViewport'),
            vgrid: document.getElementById('previewGrid'),
            spacer: document.getElementById('previewSpacer'),
            resultsPanel: document.getElementById('resultsPanel'),
            resultsGrid: document.getElementById('resultsGrid'),
            progressContainer: document.getElementById('progressContainer'),
            progressFill: document.getElementById('progressFill'),
            progressPercentage: document.getElementById('progressPercentage'),
            progressStatus: document.getElementById('progressStatus'),
            cameraModal: document.getElementById('cameraModal'),
            cameraVideo: document.getElementById('cameraVideo'),
            cameraCanvas: document.getElementById('cameraCanvas'),
            openCameraBtn: document.getElementById('openCameraBtn'),
            captureBtn: document.getElementById('captureBtn'),
            closeCameraBtn: document.getElementById('closeCameraBtn'),
            clearAllBtn: document.getElementById('clearAllBtn'),
            toastHost: document.getElementById('toastHost')
        };
    }

    init() {
        // NEW: Check authentication on init
        if (!window.isAuthenticated || !window.isAuthenticated()) {
            window.location.href = '/login';
            return;
        }
        
        this.initDropzone();
        this.initCamera();
        this.initForm();
        this.bindEvents();
        console.log('✅ PhotoMaker UI initialized');
    }

    // NEW: Get JWT token for API requests
    getAuthHeaders() {
        const token = localStorage.getItem('jwt_token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }

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
            dropzone.addEventListener(eventName, () => dropzone.classList.add('drag'));
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => dropzone.classList.remove('drag'));
        });

        // Handle drop
        dropzone.addEventListener('drop', (e) => {
            const files = Array.from(e.dataTransfer.files || []);
            if (files.length) this.addFiles(files);
        });

        // Handle dropzone click
        dropzone.addEventListener('click', (e) => {
            if (e.target !== fileInput) {
                e.preventDefault();
                fileInput.click();
            }
        });

        // Handle keyboard activation
        dropzone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInput.click();
            }
        });

        // Handle file input change
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files || []);
            if (files.length) {
                this.addFiles(files);
                this.showToast(`Selected ${files.length} image${files.length > 1 ? 's' : ''}`, 'good');
            }
            e.target.value = ''; // Reset input
        });
    }

    async addFiles(files) {
        const imageFiles = files.filter(f => f && f.type && f.type.startsWith('image/'));
        
        if (!imageFiles.length) {
            this.showToast('No valid images selected', 'bad');
            return;
        }
        
        if (this.items.length + imageFiles.length > 10) {
            this.showToast(`Maximum 10 files allowed. Currently have ${this.items.length}`, 'bad');
            return;
        }

        // Process files
        for (const file of imageFiles) {
            try {
                let processedFile = file;
                const fileSizeMB = file.size / 1024 / 1024;
                
                // Compress files larger than 3MB
                if (fileSizeMB > 3) {
                    this.showToast(`Compressing ${file.name}...`, 'info');
                    processedFile = await this.compressImage(file);
                }

                // Add to items
                this.items.push({
                    file: processedFile,
                    id: this.idSeq++,
                    design: '',
                    url: URL.createObjectURL(processedFile)
                });
            } catch (error) {
                console.error(`Error processing ${file.name}:`, error);
                this.showToast(`Failed to process ${file.name}`, 'bad');
            }
        }

        this.showToast(`Added ${imageFiles.length} image${imageFiles.length > 1 ? 's' : ''}`, 'good');
        this.updateLayout();
    }

    async compressImage(file) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                let { width, height } = img;
                const maxDimension = 2000;
                
                if (width > maxDimension || height > maxDimension) {
                    const ratio = Math.min(maxDimension / width, maxDimension / height);
                    width *= ratio;
                    height *= ratio;
                }
                
                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);
                
                canvas.toBlob((blob) => {
                    const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, '.jpg'), {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    });
                    resolve(compressedFile);
                }, 'image/jpeg', 0.85);
            };
            
            img.src = URL.createObjectURL(file);
        });
    }

    initCamera() {
        const { openCameraBtn, captureBtn, closeCameraBtn } = this.elements;
        
        if (openCameraBtn) openCameraBtn.addEventListener('click', () => this.openCamera());
        if (captureBtn) captureBtn.addEventListener('click', () => this.captureFromCamera());
        if (closeCameraBtn) closeCameraBtn.addEventListener('click', () => this.closeCamera());
    }

    async openCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' },
                audio: false
            });
            
            this.elements.cameraVideo.srcObject = this.stream;
            this.elements.cameraModal.style.display = 'flex';
            this.showToast('Camera ready! Position your item and capture', 'good');
        } catch (error) {
            console.error('Camera error:', error);
            this.showToast('Camera not available', 'bad');
        }
    }

    async captureFromCamera() {
        if (!this.stream) return;
        
        const { cameraVideo, cameraCanvas } = this.elements;
        const w = cameraVideo.videoWidth;
        const h = cameraVideo.videoHeight;
        
        if (!w || !h) {
            this.showToast('Camera not ready', 'bad');
            return;
        }
        
        cameraCanvas.width = w;
        cameraCanvas.height = h;
        
        const ctx = cameraCanvas.getContext('2d');
        ctx.drawImage(cameraVideo, 0, 0, w, h);
        
        try {
            const blob = await new Promise(resolve => cameraCanvas.toBlob(resolve, 'image/jpeg', 0.9));
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            const file = new File([blob], `camera-${timestamp}.jpg`, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });
            
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
        this.elements.cameraModal.style.display = 'none';
    }

    initForm() {
        if (this.elements.form) {
            this.elements.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
        
        if (this.elements.clearAllBtn) {
            this.elements.clearAllBtn.addEventListener('click', () => this.clearAll());
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        if (this.isProcessing) return;
        
        if (!this.items.length) {
            this.showToast('No images to process', 'bad');
            return;
        }
        
        if (!this.elements.catalogSelect?.value) {
            this.showToast('Please select a catalog', 'bad');
            return;
        }

        this.isProcessing = true;
        
        try {
            const formData = new FormData();
            formData.append('catalog', this.elements.catalogSelect.value);
            
            const mapping = this.items.map((item, index) => ({
                index,
                design_number: item.design || `Design_${index + 1}`
            }));
            formData.append('mapping', JSON.stringify(mapping));
            
            this.items.forEach(item => formData.append('files', item.file));
            
            this.showProgress();
            
            // CHANGED: Use new backend endpoint with JWT auth
            const response = await fetch(`${window.API_BASE_URL}/api/v1/platemaker/upload`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.displayResults(data);
                const successCount = data.results.filter(r => r.status === 'success').length;
                this.showToast(`Successfully processed ${successCount} images`, 'good');
            } else {
                // Handle JWT token expiry
                if (response.status === 401) {
                    this.showToast('Session expired. Please login again.', 'bad');
                    setTimeout(() => window.location.href = '/login', 2000);
                } else {
                    this.showToast(data.error || 'Upload failed', 'bad');
                }
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showToast('Upload failed. Please try again.', 'bad');
        } finally {
            this.isProcessing = false;
            this.hideProgress();
        }
    }

    // Rest of the methods remain UNCHANGED...
    updateLayout() {
        if (!this.elements.vgrid) return;
        
        this.elements.vgrid.innerHTML = '';
        
        this.items.forEach((item, index) => {
            const row = Math.floor(index / this.colCount);
            const col = index % this.colCount;
            const x = col * (this.cardW + this.gap);
            const y = row * (this.cardH + this.gap);
            
            const card = this.createCard(item, x, y);
            this.elements.vgrid.appendChild(card);
        });
        
        const totalRows = Math.ceil(this.items.length / this.colCount);
        const totalHeight = totalRows * (this.cardH + this.gap);
        
        if (this.elements.spacer) {
            this.elements.spacer.style.height = `${totalHeight}px`;
        }
    }

    createCard(item, x, y) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cssText = `
            position: absolute;
            transform: translate(${x}px, ${y}px);
            width: ${this.cardW}px;
        `;
        
        card.innerHTML = `
            <img src="${item.url}" class="thumb" alt="Preview">
            <div class="card-body">
                <input 
                    type="text" 
                    class="input" 
                    placeholder="Design name" 
                    value="${item.design}"
                    onchange="photoMakerUI.updateDesign(${item.id}, this.value)"
                >
                <button onclick="photoMakerUI.removeItem(${item.id})" class="remove-btn">×</button>
            </div>
        `;
        
        return card;
    }

    updateDesign(id, value) {
        const item = this.items.find(i => i.id === id);
        if (item) {
            item.design = value;
        }
    }

    removeItem(id) {
        this.items = this.items.filter(i => i.id !== id);
        this.updateLayout();
        this.showToast('Image removed', 'info');
    }

    clearAll() {
        this.items = [];
        this.updateLayout();
        this.showToast('All images cleared', 'info');
    }

    showProgress() {
        if (this.elements.progressContainer) {
            this.elements.progressContainer.style.display = 'block';
        }
    }

    hideProgress() {
        if (this.elements.progressContainer) {
            this.elements.progressContainer.style.display = 'none';
        }
    }

    displayResults(data) {
        if (!this.elements.resultsPanel || !this.elements.resultsGrid) return;
        
        this.elements.resultsPanel.style.display = 'block';
        this.elements.resultsGrid.innerHTML = '';
        
        data.results.forEach(result => {
            const resultEl = document.createElement('div');
            resultEl.className = 'result';
            resultEl.innerHTML = `
                <div class="result-head">
                    <span class="status ${result.status === 'success' ? 'ok' : 'err'}"></span>
                    <span class="result-name">${result.filename}</span>
                </div>
                ${result.url ? `<a href="${result.url}" class="link" target="_blank">View Image</a>` : ''}
                ${result.error ? `<div class="error">${result.error}</div>` : ''}
                ${result.note ? `<div class="note">${result.note}</div>` : ''}
            `;
            this.elements.resultsGrid.appendChild(resultEl);
        });
    }

    showToast(message, type = 'info') {
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    bindEvents() {
        // Handle window resize
        window.addEventListener('resize', () => {
            const newColCount = Math.floor((window.innerWidth - 100) / (this.cardW + this.gap)) || 2;
            if (newColCount !== this.colCount) {
                this.colCount = newColCount;
                this.updateLayout();
            }
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.photoMakerUI = new PhotoMakerUI();
});
