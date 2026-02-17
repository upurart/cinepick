document.addEventListener('DOMContentLoaded', function() {
    // ======================================================
    // 1. GLOBAL VARIABLES
    // ======================================================
    const itemsPerGroup = 5;
    const itemWidth = 100 / itemsPerGroup; // 20%
    let isSliding = false;
    const sliderIndices = {};

    // ======================================================
    // 0. URL oluşturucu
    // ======================================================
    function getMediaUrl(movie) {
        const type = movie.media_type || 'movie';
        return `/content/${type}/${movie.id}`;
    }

    // ======================================================
    // 2. UI(Arayüz) senkronizasyonu
    // ======================================================
    window.syncUI = function(movieId, inWatchlist) {
        const allInstances = document.querySelectorAll(`.weekly-slide-item[data-movie-id="${movieId}"]`);
        allInstances.forEach(card => {
            const icon = card.querySelector('i');
            if (icon) {
                icon.className = inWatchlist ? 'fas fa-bookmark' : 'far fa-bookmark';
            }
        });

        if (typeof movieData !== 'undefined') {
            const targetMovie = movieData.find(m => m.id == movieId);
            if (targetMovie) {
                targetMovie.in_watchlist = inWatchlist;
                const mainTitle = document.getElementById('main-title');
                const heroBtn = document.getElementById('add-to-watchlist');
                if (mainTitle && heroBtn && mainTitle.textContent.trim() === targetMovie.title) {
                    if (inWatchlist) {
                        heroBtn.innerHTML = '<i class="fas fa-bookmark"></i>';
                        heroBtn.style.color = '#fff'; heroBtn.style.border = 'none';
                    } else {
                        heroBtn.innerHTML = '<i class="far fa-bookmark"></i>';
                        heroBtn.style.backgroundColor = ''; heroBtn.style.color = ''; heroBtn.style.border = '';
                    }
                }
            }
        }
    };

    // ======================================================
    // 3. Ana Slider
    // ======================================================
    if (typeof movieData !== 'undefined' && movieData.length > 0) {
        const elements = {
            backdropImg: document.getElementById('main-backdrop'),
            posterImg: document.getElementById('main-poster'),
            titleText: document.getElementById('main-title'),
            descriptionText: document.querySelector('.main-description p'),
            ratingText: document.getElementById('main-rating'),
            ratingStar: document.getElementById('ratingStar'),
            releaseDateText: document.getElementById('main-release-date'),
            genreText: document.getElementById('main-genre-text'),
            detailsBtn: document.getElementById('main-details-btn'),
            addToWatchlistBtn: document.getElementById('add-to-watchlist'),
            prevBtn: document.querySelector('.prev-btn'),
            nextBtn: document.querySelector('.next-btn'),
            dotsContainer: document.getElementById('slider-dots'),
            upNextList: document.getElementById('upNextList') || document.getElementById('up-next-list')
        };

        if (elements.posterImg && elements.prevBtn && elements.nextBtn) {
            let currentIndex = 0;
            let slideInterval = null;

            window.handleWatchlistClick = function(e, movie) {
                if(e) e.preventDefault();
                const btn = elements.addToWatchlistBtn;
                if (!btn) return;

                const mediaType = movie.media_type || 'movie';
                const url = movie.in_watchlist
                    ? `/remove_from_watchlist/${mediaType}/${movie.id}`
                    : `/add_to_watchlist/${mediaType}/${movie.id}`;

                btn.disabled = true;

                fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'} })
                .then(r => r.json()).then(data => {
                    if (data.status === 'success' || data.status === 'removed' || data.status === 'exists') {
                        const newState = !movie.in_watchlist;
                        movie.in_watchlist = newState;

                        if (typeof window.updateWatchlistVisuals === 'function') {
                            const movieDataObj = {
                                id: movie.id,
                                media_type: mediaType,
                                title: movie.title,
                                poster: movie.poster,
                                rating: movie.rating,
                                release_date: movie.release_date
                            };
                            window.updateWatchlistVisuals(newState ? 'add' : 'remove', movieDataObj);
                        }
                        window.syncUI(movie.id, newState);
                        showNotification(newState ? 'Listeye eklendi' : 'Listeden çıkarıldı', 'success');
                    } else { alert(data.message); }
                })
                .catch(err => { console.error(err); btn.innerHTML = 'Hata'; })
                .finally(() => { btn.disabled = false; });
            };

            function updateSlider(index) {
                if (index < 0) currentIndex = movieData.length - 1;
                else if (index >= movieData.length) currentIndex = 0;
                else currentIndex = index;
                const movie = movieData[currentIndex];
                const fadeItems = [elements.backdropImg, elements.posterImg, elements.titleText, elements.ratingText, elements.ratingStar, elements.genreText, elements.releaseDateText, elements.descriptionText, elements.detailsBtn, elements.addToWatchlistBtn];
                fadeItems.forEach(el => { if(el) el.style.opacity = '0'; });

                setTimeout(() => {
                    elements.backdropImg.src = movie.backdrop;
                    elements.posterImg.src = movie.poster;
                    elements.titleText.textContent = movie.title;
                    elements.ratingText.textContent = movie.rating;
                    elements.genreText.textContent = movie.genres || "";
                    elements.releaseDateText.textContent = movie.release_date;
                    if(elements.descriptionText) elements.descriptionText.textContent = movie.overview || "Açıklama yok.";

                    elements.detailsBtn.onclick = () => window.location.href = getMediaUrl(movie);

                    if (elements.addToWatchlistBtn) {
                        if (movie.in_watchlist) {
                            elements.addToWatchlistBtn.innerHTML = '<i class="fas fa-bookmark"></i>';
                            elements.addToWatchlistBtn.style.color = '#fff'; elements.addToWatchlistBtn.style.border = 'none';
                        } else {
                            elements.addToWatchlistBtn.innerHTML = '<i class="far fa-bookmark"></i>';
                            elements.addToWatchlistBtn.style.backgroundColor = ''; elements.addToWatchlistBtn.style.color = ''; elements.addToWatchlistBtn.style.border = '';
                        }
                        elements.addToWatchlistBtn.onclick = (e) => handleWatchlistClick(e, movie);
                    }
                    fadeItems.forEach(el => { if(el) el.style.opacity = '1'; });
                }, 200);
                updateDots(); updateUpNextList(currentIndex);
            }

            function updateUpNextList(idx) {
                if(!elements.upNextList) return;
                elements.upNextList.innerHTML = '';
                for(let i=1; i<=4; i++) {
                    let nextIdx = (idx + i) % movieData.length;
                    let m = movieData[nextIdx];
                    let div = document.createElement('div');
                    div.className = 'next-movie-card';
                    div.onclick = () => { updateSlider(nextIdx); resetTimer(); };
                    div.innerHTML = `<img src="${m.poster}" class="next-movie-img"><div class="next-movie-info"><div class="next-movie-title">${m.title}</div><div class="next-movie-rating"><i class="fas fa-star"></i> ${m.rating}</div></div>`;
                    elements.upNextList.appendChild(div);
                }
            }
            function createDots() {
                if(!elements.dotsContainer) return;
                elements.dotsContainer.innerHTML = '';
                movieData.forEach((_, i) => {
                    let d = document.createElement('div'); d.className = 'dot';
                    if(i===0) d.classList.add('active');
                    d.onclick = () => { updateSlider(i); resetTimer(); };
                    elements.dotsContainer.appendChild(d);
                });
            }
            function updateDots() { document.querySelectorAll('.dot').forEach((d, i) => { if(i === currentIndex) d.classList.add('active'); else d.classList.remove('active'); }); }
            function startTimer() { if(slideInterval) clearInterval(slideInterval); slideInterval = setInterval(() => updateSlider(currentIndex+1), 6000); }
            function resetTimer() { clearInterval(slideInterval); startTimer(); }

            elements.nextBtn.onclick = () => { updateSlider(currentIndex+1); resetTimer(); };
            elements.prevBtn.onclick = () => { updateSlider(currentIndex-1); resetTimer(); };
            createDots(); updateSlider(0); startTimer();
        }
    }



    // ======================================================
    // 4. Haftalık & İzleme listesi sliderları
    // ======================================================
    const tracks = document.querySelectorAll('.weekly-slider-track');
    tracks.forEach(track => { initSlider(track.id); });

    function initSlider(trackId) {
        const track = document.getElementById(trackId);
        if (!track || track.children.length === 0) return;
        const container = track.closest('.weekly-slider-container');
        if (!container) return;

        if (trackId === 'watchlist-track') {
            track.querySelectorAll('.clone').forEach(c => c.remove());
            const items = track.querySelectorAll('.weekly-slide-item:not(.clone)');
            const realCount = items.length;
            const prevBtn = container.querySelector('.weekly-slider-btn.prev');
            const nextBtn = container.querySelector('.weekly-slider-btn.next');

            if (realCount <= itemsPerGroup) {
                if(prevBtn) prevBtn.style.display = 'none';
                if(nextBtn) nextBtn.style.display = 'none';
                track.style.transform = 'translateX(0)';
                sliderIndices[trackId] = 0;
            } else {
                if(prevBtn) prevBtn.style.display = 'flex';
                if(nextBtn) nextBtn.style.display = 'flex';
                if (typeof sliderIndices[trackId] === 'undefined') {
                    sliderIndices[trackId] = 0;
                    track.style.transform = 'translateX(0)';
                }
            }
            track.classList.add('initialized');
            return;
        }

        track.querySelectorAll('.clone').forEach(c => c.remove());
        const items = Array.from(track.children);
        const realCount = items.length;
        const prevBtn = container.querySelector('.weekly-slider-btn.prev');
        const nextBtn = container.querySelector('.weekly-slider-btn.next');

        if (realCount <= itemsPerGroup) {
            if(prevBtn) prevBtn.style.display = 'none';
            if(nextBtn) nextBtn.style.display = 'none';
            track.classList.add('no-transition');
            track.style.transform = 'translateX(0)';
            return;
        } else {
            if(prevBtn) prevBtn.style.display = 'flex';
            if(nextBtn) nextBtn.style.display = 'flex';
        }

        track.classList.remove('no-infinite');
        const clonesCount = itemsPerGroup;
        const clonesStart = items.slice(-clonesCount).map(i => { const c=i.cloneNode(true); c.classList.add('clone'); return c; });
        const clonesEnd = items.slice(0, clonesCount).map(i => { const c=i.cloneNode(true); c.classList.add('clone'); return c; });

        clonesStart.reverse().forEach(c => track.prepend(c));
        clonesEnd.forEach(c => track.append(c));

        track.classList.add('initialized');
        const startIndex = itemsPerGroup;
        sliderIndices[trackId] = startIndex;
        track.classList.add('no-transition');
        track.style.transform = `translateX(-${startIndex * itemWidth}%)`;
        void track.offsetWidth;
        setTimeout(() => track.classList.remove('no-transition'), 50);
    }

    // --- MOVEMENT ---
    window.moveSlider = function(trackId, direction) {
        if (isSliding) return;
        const track = document.getElementById(trackId);
        if (!track) return;

        if (trackId === 'watchlist-track') {
            const realItems = track.querySelectorAll('.weekly-slide-item:not(.clone)');
            const totalItems = realItems.length;
            if (totalItems <= itemsPerGroup) return;

            let current = sliderIndices[trackId] || 0;
            const maxIndex = totalItems - itemsPerGroup;

            isSliding = true;
            track.style.transition = 'transform 0.5s ease';

            if (direction === 1) {
                if (current < maxIndex) {
                    current += itemsPerGroup;
                    if (current > maxIndex) current = maxIndex;
                } else {
                    current = 0;
                }
            } else {
                if (current > 0) {
                    current -= itemsPerGroup;
                    if (current < 0) current = 0;
                } else {
                    current = maxIndex;
                }
            }

            sliderIndices[trackId] = current;
            track.style.transform = `translateX(-${current * itemWidth}%)`;
            setTimeout(() => { isSliding = false; }, 500);
            return;
        }

        const realCount = track.querySelectorAll('.weekly-slide-item:not(.clone)').length;
        if (realCount <= itemsPerGroup) return;

        let current = sliderIndices[trackId];
        isSliding = true;
        current += (direction * itemsPerGroup);
        sliderIndices[trackId] = current;

        track.classList.remove('no-transition');
        track.style.transform = `translateX(-${current * itemWidth}%)`;

        setTimeout(() => {
            const minIndex = itemsPerGroup;
            const maxIndex = itemsPerGroup + realCount;

            if (current < minIndex) {
                track.classList.add('no-transition');
                current = current + realCount;
                track.style.transform = `translateX(-${current * itemWidth}%)`;
                sliderIndices[trackId] = current;
            }
            else if (current >= maxIndex) {
                track.classList.add('no-transition');
                current = current - realCount;
                track.style.transform = `translateX(-${current * itemWidth}%)`;
                sliderIndices[trackId] = current;
            }

            void track.offsetWidth;
            setTimeout(() => {
                track.classList.remove('no-transition');
                isSliding = false;
            }, 50);

        }, 550);
    };

    // ======================================================
    // 5. Yardımcı Fonksiyonlar
    // ======================================================
    window.checkWatchlistArrows = function() {
        const track = document.getElementById('watchlist-track');
        if (!track) return;
        const container = track.closest('.weekly-slider-container');
        if (!container) return;

        const realItems = track.querySelectorAll('.weekly-slide-item:not(.clone)');
        const prevBtn = container.querySelector('.weekly-slider-btn.prev');
        const nextBtn = container.querySelector('.weekly-slider-btn.next');

        if (realItems.length <= itemsPerGroup) {
            if(prevBtn) prevBtn.style.setProperty('display', 'none', 'important');
            if(nextBtn) nextBtn.style.setProperty('display', 'none', 'important');
        } else {
            if(prevBtn) prevBtn.style.display = 'flex';
            if(nextBtn) nextBtn.style.display = 'flex';
        }
    };

    window.checkIfSliderEmpty = function() {
        const track = document.getElementById('watchlist-track');
        if (!track) return;
        const items = track.querySelectorAll('.weekly-slide-item:not(.clone)');
        const emptyState = document.getElementById('watchlist-empty-state');
        const container = track.closest('.weekly-slider-container');

        if (items.length === 0) {
            if (emptyState) {
                emptyState.style.display = 'block';
                emptyState.style.opacity = '0';
                emptyState.style.transition = 'opacity 0.5s ease';
                setTimeout(() => {
                    emptyState.style.opacity = '1';
                }, 50);
            }
            if (container) container.style.display = 'none';
        }
    };

    window.showNotification = function(message, type) {
        const existingNotif = document.querySelector('.notification');
        if (existingNotif) existingNotif.remove();
        const notif = document.createElement('div');
        notif.className = `notification ${type}`;
        notif.innerHTML = `<i class="fas fa-info-circle"></i> ${message}`;
        document.body.appendChild(notif);
        setTimeout(() => notif.classList.add('hide'), 3000);
        setTimeout(() => notif.remove(), 3300);
    };



    // ======================================================
    // 6. DOM UPDATE (Etiket Hizalama)
    // ======================================================
    window.updateWatchlistVisuals = function(action, movie) {
        const track = document.getElementById('watchlist-track');
        const emptyState = document.getElementById('watchlist-empty-state');
        const container = document.getElementById('watchlist-container');

        if (!track) return;

        if (typeof isSliding !== 'undefined') isSliding = false;

        if (action === 'add') {
            if (track.querySelector(`[data-movie-id="${movie.id}"]`)) return;

            if (container) container.style.display = 'block';
            if (emptyState) emptyState.style.display = 'none';
            track.style.display = 'flex';

            const newCard = document.createElement('div');
            newCard.className = 'weekly-slide-item';
            newCard.setAttribute('data-movie-id', movie.id);
            const linkUrl = getMediaUrl(movie);
            newCard.onclick = () => window.location.href = linkUrl;

            newCard.style.opacity = '0';
            newCard.style.transition = 'opacity 0.5s ease';

            const mType = movie.media_type || 'movie';
            const typeLabel = (mType === 'tv') ? 'DİZİ' : 'FİLM';

            // --- HTML TASARIMI GÜNCELLENDİ (FLEXBOX İLE HİZALAMA) ---
            newCard.innerHTML = `
                <div class="watchlist-btn">
                    <button class="add-item-btn"
                            onclick="toggleCardWatchlist(event, this, '${mType}', '${movie.id}')"
                            title="Listeden Kaldır">
                        <i class="fas fa-bookmark"></i>
                    </button>
                </div>

                <div class="weekly-movie-card-design watchlist-card">
                    <div class="weekly-image-container">
                        <img src="${movie.poster}" loading="lazy" style="width:100%; height:100%; object-fit:cover;">
                        <div class="weekly-rating-badge"> <i class="fas fa-star"></i>${movie.rating}</div>
                    </div>

                    <div class="weekly-text-content">
                        <h3 class="weekly-movie-title">${movie.title}</h3>

                        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 5px;">
                            <p class="weekly-movie-date" style="margin: 0; line-height: 1;">${movie.release_date}</p>

                            <span style="font-size: 0.7rem; text-transform: uppercase; border: 1px solid #555; padding: 2px 6px; border-radius: 4px; color: #888; display: inline-block; line-height: 1;">
                                ${typeLabel}
                            </span>
                        </div>
                    </div>
                </div>`;

            // Animasyon çakışmasını önleyen listener
            newCard.addEventListener('mouseenter', function removeInlineTransition() {
                this.style.transition = '';
                void this.offsetWidth;
                this.removeEventListener('mouseenter', removeInlineTransition);
            });

            track.prepend(newCard);

            setTimeout(() => {
                newCard.style.opacity = '1';
                setTimeout(() => {
                    newCard.style.transition = '';
                    void newCard.offsetWidth;
                }, 550);
            }, 50);

            if (typeof window.initSlider === 'function') window.initSlider('watchlist-track');
            checkWatchlistArrows();

        } else if (action === 'remove') {
            const cardToRemove = track.querySelector(`.weekly-slide-item[data-movie-id="${movie.id}"]:not(.clone)`);
            if (cardToRemove) {
                cardToRemove.style.transition = 'all 0.5s ease';
                cardToRemove.style.opacity = '0';
                cardToRemove.style.transform = 'scale(0)';
                cardToRemove.style.maxWidth = '0px';
                cardToRemove.style.padding = '0px';
                cardToRemove.style.margin = '0px';
                cardToRemove.style.overflow = 'hidden';

                setTimeout(() => {
                    cardToRemove.remove();
                    if (typeof window.initSlider === 'function') window.initSlider('watchlist-track');
                    checkIfSliderEmpty();
                    checkWatchlistArrows();
                }, 500);
            }
        }
    };

    /* User Menu
    const userMenu = document.getElementById('user-menu');
    if (userMenu) {
        userMenu.querySelector('.user-menu-btn').addEventListener('click', (e) => { e.stopPropagation(); userMenu.classList.toggle('active'); });
        document.addEventListener('click', (e) => { if (!userMenu.contains(e.target)) userMenu.classList.remove('active'); });
    }*/

    const userMenu = document.getElementById('user-menu');

    if (userMenu) {
        // Önce butonu bir değişkene atayalım
        const menuBtn = userMenu.querySelector('.user-menu-btn');

        // Butonun gerçekten var olup olmadığını kontrol edelim
        if (menuBtn) {
            menuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                userMenu.classList.toggle('active');
            });
        }

        // Menü dışına tıklayınca kapanma olayı
        document.addEventListener('click', (e) => {
            if (!userMenu.contains(e.target)) {
                userMenu.classList.remove('active');
            }
        });
    }
});

// ======================================================
// Global Fonksiyonlar
// ======================================================

function toggleCardWatchlist(event, btnElement, mediaType, movieId) {
    if(event) {
        event.stopPropagation();
        event.preventDefault();
    }

    if (!mediaType || mediaType === 'undefined') mediaType = 'movie';

    const clickedIcon = btnElement.querySelector('i');
    const isAdding = clickedIcon.classList.contains('far');

    let movieDataObj = { id: movieId, media_type: mediaType };

    const cardItem = btnElement.closest('.weekly-slide-item') || btnElement.closest('.movie-card') || btnElement.closest('.actor-movie-card');

    if (cardItem) {
        const img = cardItem.querySelector('img');
        const title = cardItem.querySelector('.weekly-movie-title') || cardItem.querySelector('h3') || cardItem.querySelector('.movie-title');
        const rating = cardItem.querySelector('.weekly-rating-badge') || cardItem.querySelector('.rating-badge') || cardItem.querySelector('.card-rating-badge');
        const date = cardItem.querySelector('.weekly-movie-date') || cardItem.querySelector('.date') || cardItem.querySelector('.movie-date');

        movieDataObj.poster = img ? img.src : '';
        movieDataObj.title = title ? title.textContent.trim() : '';
        movieDataObj.rating = rating ? rating.textContent.trim().replace(/[^\d.]/g, '') : '';
        movieDataObj.release_date = date ? date.textContent.trim() : '';
    }

    const url = isAdding
        ? `/add_to_watchlist/${mediaType}/${movieId}`
        : `/remove_from_watchlist/${mediaType}/${movieId}`;

    btnElement.disabled = true;

    fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'} })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success' || data.status === 'removed' || data.status === 'exists') {
            updateIconVisual(clickedIcon, isAdding);

            const relatedButtons = document.querySelectorAll(`button[onclick*="'${movieId}'"]`);
            relatedButtons.forEach(btn => {
                if (btn !== btnElement) {
                    const icon = btn.querySelector('i');
                    if (icon) updateIconVisual(icon, isAdding);
                }
            });

            if (typeof updateWatchlistVisuals === 'function') {
                updateWatchlistVisuals(isAdding ? 'add' : 'remove', movieDataObj);
            }
            if (typeof syncUI === 'function') {
                syncUI(movieId, isAdding);
            }
            showNotification(isAdding ? 'Listeye eklendi' : 'Listeden çıkarıldı', 'success');
        }
    })
    .catch(console.error)
    .finally(() => {
        btnElement.disabled = false;
    });
}

function updateIconVisual(iconElement, isAdding) {
    if (isAdding) {
        iconElement.classList.remove('far');
        iconElement.classList.add('fas');
    } else {
        iconElement.classList.remove('fas');
        iconElement.classList.add('far');
    }
}

window.toggleCardWatchlist = toggleCardWatchlist;

window.removeFromWatchlist = function(mediaType, movieId, btnElement) {
    toggleCardWatchlist(null, btnElement, mediaType, movieId);
};