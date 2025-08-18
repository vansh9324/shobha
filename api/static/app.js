// ========== PHOTO MAKER UI (COMPLETE WORKING VERSION) ==========
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
        this.initDropzone();
        this.initCamera();
        this.initForm();
        this.bindEvents();
        console.log('✅ PhotoMaker UI initialized');
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
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showToast('Upload failed. Please try again.', 'bad');
        } finally {
            this.isProcessing = false;
            this.hideProgress();
        }
    }
    
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
            <img class="thumb" src="${item.url}" alt="Preview" style="width: 100%; height: 120px; object-fit: cover;">
            <div class="card-body">
                <input 
                    class="input" 
                    placeholder="Design Number" 
                    value="${item.design}" 
                    data-item-id="${item.id}"
                >
            </div>
        `;
        
        const input = card.querySelector('.input');
        input.addEventListener('input', (e) => {
            const itemIndex = this.items.findIndex(i => i.id === parseInt(e.target.dataset.itemId));
            if (itemIndex !== -1) {
                this.items[itemIndex].design = e.target.value;
            }
        });
        
        return card;
    }
    
    clearAll() {
        this.items.forEach(item => {
            if (item.url) URL.revokeObjectURL(item.url);
        });
        this.items = [];
        this.updateLayout();
        this.showToast('All images cleared', 'info');
    }
    
    showProgress() {
        if (this.elements.progressContainer) {
            this.elements.progressContainer.style.display = 'block';
            this.animateProgress();
        }
        if (this.elements.processBtn) {
            this.elements.processBtn.style.display = 'none';
        }
    }
    
    hideProgress() {
        setTimeout(() => {
            if (this.elements.progressContainer) {
                this.elements.progressContainer.style.display = 'none';
            }
            if (this.elements.processBtn) {
                this.elements.processBtn.style.display = 'block';
            }
        }, 1000);
    }
    
    animateProgress() {
        let progress = 0;
        const interval = setInterval(() => {
            if (!this.isProcessing) {
                clearInterval(interval);
                progress = 100;
            } else {
                progress += Math.random() * 15;
                if (progress > 90) progress = 90;
            }
            
            if (this.elements.progressFill) {
                this.elements.progressFill.style.width = `${progress}%`;
            }
            if (this.elements.progressPercentage) {
                this.elements.progressPercentage.textContent = `${Math.round(progress)}%`;
            }
            
            if (progress >= 100) {
                clearInterval(interval);
                if (this.elements.progressStatus) {
                    this.elements.progressStatus.textContent = 'Complete!';
                }
            }
        }, 200);
    }
    
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
                ${result.status === 'success' && result.url ? 
                    `<a href="${result.url}" target="_blank" class="link">View in Drive →</a>` :
                    `<div style="color: #ff5c5c; font-size: 0.8rem;">${result.error || 'Failed'}</div>`
                }
            `;
            this.elements.resultsGrid.appendChild(div);
        });
        
        if (this.elements.resultsPanel) {
            this.elements.resultsPanel.style.display = 'block';
        }
    }
    
    bindEvents() {
        // Window resize
        window.addEventListener('resize', () => {
            this.cardW = window.innerWidth <= 768 ? 140 : 160;
            this.colCount = Math.floor((window.innerWidth - 100) / (this.cardW + this.gap)) || 2;
            this.updateLayout();
        });
    }
    
    showToast(message, type = 'info') {
        if (!this.elements.toastHost) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        this.elements.toastHost.appendChild(toast);
        
        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 300);
        }, 3000);
        
        toast.addEventListener('click', () => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 300);
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.photoMakerUI = new PhotoMakerUI();
});
