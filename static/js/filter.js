document.addEventListener('DOMContentLoaded', () => {
    
    

    // --- 1. Accordion (Açılır/Kapanır Menü) Mantığı ---
    const filterHeaders = document.querySelectorAll('.group-header');

    filterHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const group = header.parentElement;
            group.classList.toggle('open');
        });
    });

    // --- 2. Slider Görsel Güncelleme ---
    const ratingRange = document.getElementById('rating-range');
    const ratingVal = document.getElementById('rating-val');

    if (ratingRange) {
        ratingRange.addEventListener('input', (e) => {
            ratingVal.textContent = e.target.value;
        });
    }

    // --- 3. Tür Seçimi ---
    const genreTags = document.querySelectorAll('.genre-tag');
    genreTags.forEach(tag => {
        tag.addEventListener('click', () => {
            tag.classList.toggle('active');
        });
    });

    // Sayfa yüklendiğinde eski filtreleri geri getir
    restoreFiltersFromURL();
});



// --- Filtreleri Uygula ve Sayfayı Yenile ---
function applyFilters() {
    const sortValue = document.getElementById('sort-select').value;
    const ratingValue = document.getElementById('rating-range').value;
    const currentMediaType = document.getElementById('current-media-type').value;

    // Seçili türleri topla
    const selectedGenres = Array.from(document.querySelectorAll('.genre-tag.active'))
                                .map(tag => tag.getAttribute('data-value'))
                                .join(',');

    // URL Parametrelerini Oluştur
    const params = new URLSearchParams();
    
    // Medya türünü ekle
    if (currentMediaType && currentMediaType !== 'all') {
        params.set('type', currentMediaType);
    } else {
        params.set('type', 'all');
    }

    params.set('sort', sortValue);
    
    if(ratingValue > 0) params.set('rating', ratingValue);
    if(selectedGenres) params.set('genres', selectedGenres);
    
    // Filtre değiştiğinde 1. sayfadan başla
    params.set('page', 1);

    // Sayfayı yenile
    window.location.search = params.toString();
}

// --- Filtreleri Sıfırla ---
function resetFilters() {
    const currentMediaType = document.getElementById('current-media-type').value;
    const params = new URLSearchParams();
    
    // Sadece medya türünü koru
    if (currentMediaType && currentMediaType !== 'all') {
        params.set('type', currentMediaType);
    }
    window.location.search = params.toString();
}



// --- Filtreleri URL'den Geri Yükle ---
function restoreFiltersFromURL() {
    const params = new URLSearchParams(window.location.search);
    
    // Puanı geri yükle
    if(params.has('rating')) {
        const val = params.get('rating');
        const rangeInput = document.getElementById('rating-range');
        if(rangeInput) {
            rangeInput.value = val;
            document.getElementById('rating-val').textContent = val;
        }
    }

    // Sıralamayı geri yükle
    if(params.has('sort')) {
        const sortSelect = document.getElementById('sort-select');
        if(sortSelect) {
            sortSelect.value = params.get('sort');
        }
    }

    // Türleri geri yükle
    if(params.has('genres')) {
        const ids = params.get('genres').split(',');
        ids.forEach(id => {
            const tag = document.querySelector(`.genre-tag[data-value="${id}"]`);
            if(tag) tag.classList.add('active');
        });
    }
}

// --- Sayfa Değiştir ---
function changePage(pageNumber) {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Sayfa numarasını güncelle
    urlParams.set('page', pageNumber);
    
    // Sayfayı yenile
    window.location.search = urlParams.toString();
}