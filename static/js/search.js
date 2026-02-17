// --- search.js ---

document.addEventListener('DOMContentLoaded', function() {
    
    // DOM Elementlerini Seç
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const suggestionsBox = document.getElementById('suggestions-box'); 
    
    let timeoutId; // Debounce zamanlayıcısı

    // --- MEVCUT ARAMA FONKSİYONU ---
    function searchMovie() {
        const query = searchInput.value;
        if (query.trim() !== "") {
            window.location.href = `/search?q=${encodeURIComponent(query)}`;
        }
    }


    // --- EVENT LISTENERLAR ---
    if (searchInput) {
        // Enter tuşu ile arama
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchMovie();
                if(suggestionsBox) suggestionsBox.style.display = 'none';
            }
        });

        // Canlı arama (Debounce ile)
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();

            clearTimeout(timeoutId);

            if (!suggestionsBox || query.length < 2) {
                if(suggestionsBox) {
                    suggestionsBox.style.display = 'none';
                    suggestionsBox.innerHTML = '';
                }
                return;
            }

            timeoutId = setTimeout(() => {
                fetchSuggestions(query);
            }, 300);
        });
    }

    // Arama butonu tıklaması
    if (searchBtn) {
        searchBtn.addEventListener('click', function () {
            searchMovie();
        });
    }

    

    // --- FETCH SUGGESTIONS (ÖNERİLERİ GETİR) ---
    function fetchSuggestions(query) {
        fetch(`/suggest?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                suggestionsBox.innerHTML = ''; // Temizle
                
                if (data.length > 0) {
                    suggestionsBox.style.display = 'block';
                    
                    data.forEach(movie => {
                        const mediaType = movie.media_type || 'movie';
                        const item = document.createElement('a');
                        
                        // Link ve Sınıf Atama
                        item.href = `/content/${mediaType}/${movie.id}`; 
                        item.className = 'suggestion-item';
                        
                        const typeLabel = mediaType === 'tv' ? 'DİZİ' : 'FİLM';
                        
                        // Öneri öğesi içeriği (Poster, Bilgi, Etiket)
                        item.innerHTML = `
                            <div class="poster-wrapper">
                                <img src="${movie.poster}" alt="${movie.title}">
                            </div>
                            
                            <div class="text-info">
                                <span class="suggestion-title">${movie.title}</span>
                                <span class="suggestion-year">${movie.year}</span>
                            </div>

                            <span class="media-tag">${typeLabel}</span>
                        `;
                        suggestionsBox.appendChild(item);
                    });
                } else {
                    suggestionsBox.style.display = 'none';
                }
            })
            .catch(err => console.error('Suggestion Hatası:', err));
    }

    // --- DIŞARI TIKLAYINCA KAPAT ---
    document.addEventListener('click', function(e) {
        if (suggestionsBox && searchInput) {
            if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
                suggestionsBox.style.display = 'none';
            }
        }
    });

});
