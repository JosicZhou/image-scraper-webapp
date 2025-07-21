document.addEventListener('DOMContentLoaded', () => {
    const scrapeBtn = document.getElementById('scrape-btn');
    const urlInput = document.getElementById('url-input');
    const imageCountEl = document.getElementById('image-count');
    const imageGallery = document.getElementById('image-gallery');
    const loadMoreContainer = document.getElementById('load-more-container');
    const loadMoreBtn = document.getElementById('load-more-btn');
    const stopBtn = document.getElementById('stop-btn');

    const selectAllBtn = document.getElementById('select-all-btn');
    const deselectAllBtn = document.getElementById('deselect-all-btn');
    const downloadSelectedBtn = document.getElementById('download-selected-btn');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');

    const API_URL = `${window.location.protocol}//${window.location.hostname}:5000`;
    let allImages = [];
    let currentIndex = 0;
    const batchSize = 50;

    scrapeBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            alert('Please enter a URL.');
            return;
        }

        // Reset state
        imageGallery.innerHTML = '';
        allImages = [];
        currentIndex = 0;
        loadMoreContainer.style.display = 'none';
        
        try {
            scrapeBtn.textContent = 'Scraping...';
            scrapeBtn.disabled = true;

            const response = await fetch(`${API_URL}/scrape`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            allImages = await response.json();
            imageCountEl.textContent = `Found ${allImages.length} images.`;

            renderImages();
        } catch (error) {
            alert(`Error scraping images: ${error.message}`);
            imageCountEl.textContent = 'Failed to scrape images.';
        } finally {
            scrapeBtn.textContent = 'Scrape Images';
            scrapeBtn.disabled = false;
        }
    });

    function renderImages() {
        const fragment = document.createDocumentFragment();
        const nextIndex = Math.min(currentIndex + batchSize, allImages.length);
        
        for (let i = currentIndex; i < nextIndex; i++) {
            const image = allImages[i];
            const imageCard = createImageCard(image, i);
            fragment.appendChild(imageCard);
        }

        imageGallery.appendChild(fragment);
        currentIndex = nextIndex;

        if (currentIndex < allImages.length) {
            loadMoreContainer.style.display = 'block';
        } else {
            loadMoreContainer.style.display = 'none';
        }
    }

    function createImageCard(image, index) {
        const card = document.createElement('div');
        card.className = 'image-card';
        card.dataset.index = index;
        card.dataset.imageUrl = image.src;
        card.dataset.altText = image.alt;

        const proxyUrl = `${API_URL}/proxy?url=${encodeURIComponent(image.src)}`;

        card.innerHTML = `
            <img src="${proxyUrl}" alt="${image.alt}" loading="lazy" onerror="this.src='https://via.placeholder.com/200x150?text=Image+Not+Found'; this.onerror=null;">
            <p class="alt-text" title="${image.alt}">${image.alt || 'No alt text'}</p>
            <div class="actions">
                <button class="download-btn">Download</button>
                <button class="delete-btn">Delete</button>
            </div>
            <input type="checkbox" class="checkbox">
        `;

        card.querySelector('.download-btn').addEventListener('click', (event) => downloadSingleImage(image, event));
        card.querySelector('.delete-btn').addEventListener('click', () => card.remove());
        
        return card;
    }

    async function downloadSingleImage(image, event) {
        const button = event.target.closest('button');
        try {
            button.textContent = 'Downloading...';
            button.disabled = true;

            const response = await fetch(`${API_URL}/download-image`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: image.src, alt: image.alt }),
            });

            if (!response.ok) {
                const errorResult = await response.json().catch(() => ({ error: 'An unknown error occurred' }));
                throw new Error(errorResult.error || `HTTP error! status: ${response.status}`);
            }
            
            // Get filename from 'Content-Disposition' header
            const disposition = response.headers.get('Content-Disposition');
            let filename = `${sanitizeAltForFilename(image.alt)}.jpg`; // fallback
            if (disposition && disposition.indexOf('attachment') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) { 
                  filename = matches[1].replace(/['"]/g, '');
                }
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

        } catch (error) {
            alert(`Error downloading image: ${error.message}`);
        } finally {
            if(button){
                 button.textContent = 'Download';
                 button.disabled = false;
            }
        }
    }
    
    function sanitizeAltForFilename(text) {
        return text.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    }

    loadMoreBtn.addEventListener('click', renderImages);
    stopBtn.addEventListener('click', () => {
        loadMoreContainer.style.display = 'none';
    });

    selectAllBtn.addEventListener('click', () => {
        document.querySelectorAll('.image-card .checkbox').forEach(cb => cb.checked = true);
    });

    deselectAllBtn.addEventListener('click', () => {
        document.querySelectorAll('.image-card .checkbox').forEach(cb => cb.checked = false);
    });

    deleteSelectedBtn.addEventListener('click', () => {
        document.querySelectorAll('.image-card .checkbox:checked').forEach(cb => {
            cb.closest('.image-card').remove();
        });
    });

    downloadSelectedBtn.addEventListener('click', async () => {
        const selectedImages = [];
        document.querySelectorAll('.image-card .checkbox:checked').forEach(cb => {
            const card = cb.closest('.image-card');
            selectedImages.push({
                src: card.dataset.imageUrl,
                alt: card.dataset.altText
            });
        });

        if (selectedImages.length === 0) {
            alert('No images selected.');
            return;
        }

        try {
            downloadSelectedBtn.textContent = `Downloading (${selectedImages.length})...`;
            downloadSelectedBtn.disabled = true;

            const response = await fetch(`${API_URL}/download-selected`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ images: selectedImages }),
            });

            if (!response.ok) {
                const errorResult = await response.json().catch(() => ({ error: 'An unknown error occurred' }));
                throw new Error(errorResult.error || `HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'images.zip';
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

        } catch (error) {
            alert(`Error downloading selected images: ${error.message}`);
        } finally {
            downloadSelectedBtn.textContent = 'Download Selected';
            downloadSelectedBtn.disabled = false;
        }
    });

});
