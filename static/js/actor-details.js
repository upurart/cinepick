function toggleBio() {
    const bioText = document.getElementById('bio-text');
    const btn = document.getElementById('read-more-btn');

    

    // Biyografi metninin görünürlüğünü ve buton metnini değiştirir
    if (bioText.classList.contains('collapsed')) {
        bioText.classList.remove('collapsed');
        btn.innerText = "Daha Az Göster";
    } else {
        bioText.classList.add('collapsed');
        btn.innerText = "Devamını Oku";
    }
}