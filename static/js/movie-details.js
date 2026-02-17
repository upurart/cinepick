console.log("Movie Details JS Yüklendi!");



function openTrailer(url) {
    const modal = document.getElementById('trailerModal');
    const iframe = document.getElementById('youtubeFrame');

    // Gerekli elementler yoksa işlemi durdur ve hata bas
    if (!modal || !iframe) {
        console.error("HATA: Modal veya Iframe elementi bulunamadı.");
        return;
    }

    if (url) {
        // URL yapısını kontrol et ve otomatik oynatma (autoplay) ekle
        const symbol = url.includes('?') ? '&' : '?';
        iframe.src = url + symbol + "autoplay=1";

        // Modalı görünür hale getir (CSS: display: flex)
        modal.style.display = "flex";
    } else {
        alert("Fragman linki bulunamadı!");
    }
}

function closeTrailer() {
    const modal = document.getElementById('trailerModal');
    const iframe = document.getElementById('youtubeFrame');

    // Videoyu durdurmak için iframe kaynağını temizle
    if (iframe) iframe.src = "";

    // Modalı gizle
    if (modal) modal.style.display = "none";
}

// Modalın dışındaki karanlık alana (overlay) tıklanırsa kapat
window.onclick = function(event) {
    const modal = document.getElementById('trailerModal');
    if (event.target == modal) {
        closeTrailer();
    }
}