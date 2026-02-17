// --- DEĞİŞKENLER ---
var loginForm = document.getElementById("login-form");
var registerForm = document.getElementById("register-form");
var btnHighlight = document.getElementById("btn-highlight");
var btns = document.querySelectorAll(".toggle-btn");
var container = document.querySelector(".container");

// --- HATA FONKSİYONLARI ---

function showError(input, message) {
    const wrapper = input.parentElement;
    const errorDisplay = wrapper.querySelector('.error-msg');

    if (errorDisplay) {
        errorDisplay.innerText = message;
        errorDisplay.style.color = "red";
        errorDisplay.style.fontSize = "12px";
    }
    input.classList.add('error-border');
}

function clearError(input) {
    const wrapper = input.parentElement;
    const errorDisplay = wrapper.querySelector('.error-msg');

    if (errorDisplay) {
        errorDisplay.innerText = '';
    }
    input.classList.remove('error-border');
}

function clearAllErrors() {
    const inputs = document.querySelectorAll('.input-field');
    const errors = document.querySelectorAll('.error-msg');
    inputs.forEach(input => input.classList.remove('error-border'));
    errors.forEach(error => error.innerText = '');
}



// --- TAB GEÇİŞ FONKSİYONU ---
function switchTab(tab, skipAnimation = false) {
    clearAllErrors();

    const currentHeight = container.offsetHeight;

    // Animasyon durumunu ayarla
    if (skipAnimation) {
        container.style.transition = 'none';
        btnHighlight.style.transition = 'none';
        loginForm.style.transition = 'none';
        registerForm.style.transition = 'none';
    } else {
        container.style.transition = '';
        btnHighlight.style.transition = '';
        loginForm.style.transition = '';
        registerForm.style.transition = '';
    }

    if (!skipAnimation) {
        container.style.height = currentHeight + 'px';
    }

    // Sekme görünürlüğünü ve vurguyu ayarla
    if (tab === 'register') {
        loginForm.classList.add("hidden");
        registerForm.classList.remove("hidden");

        btnHighlight.style.left = "calc(50% - 2px)";
        btns[0].classList.remove("active-text");
        btns[1].classList.add("active-text");
    } else {
        registerForm.classList.add("hidden");
        loginForm.classList.remove("hidden");

        btnHighlight.style.left = "5px";
        btns[1].classList.remove("active-text");
        btns[0].classList.add("active-text");
    }

    // Yükseklik animasyonunu yönet
    container.style.height = 'auto';
    const newHeight = container.offsetHeight;

    if (!skipAnimation) {
        container.style.height = currentHeight + 'px';

        requestAnimationFrame(() => {
            container.style.height = newHeight + 'px';
        });

        container.addEventListener('transitionend', function handler() {
            container.style.height = 'auto';
            container.removeEventListener('transitionend', handler);
        });

    } else {
        container.style.height = 'auto';

        // Animasyonları geri yükle
        setTimeout(() => {
             container.style.transition = '';
             btnHighlight.style.transition = '';
             loginForm.style.transition = '';
             registerForm.style.transition = '';
        }, 50);
    }
}

// --- DOMContentLoaded ---
document.addEventListener("DOMContentLoaded", function() {
    // Başlangıç sekmesini belirle (Flask'tan gelen veriyle)
    const initialTab = (typeof ACTIVE_TAB_FROM_FLASK !== 'undefined' && ACTIVE_TAB_FROM_FLASK === 'register')
                        ? 'register'
                        : 'login';

    // İlk yüklemede animasyonu atla
    switchTab(initialTab, true);

    // Buton tıklamalarını dinle
    btns.forEach(button => {
        const tab = button.getAttribute('data-tab');

        button.addEventListener('click', function() {
            switchTab(tab);
        });
    });
});



// --- GİRİŞ FORMU KONTROLÜ ---
if(loginForm) {
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();

        let isValid = true;
        const user = document.getElementById('login-user');
        const pass = document.getElementById('login-pass');

        if (user.value.trim() === '') {
            showError(user, 'Kullanıcı adı gerekli.');
            isValid = false;
        } else {
            clearError(user);
        }

        if (pass.value.trim() === '') {
            showError(pass, 'Şifre gerekli.');
            isValid = false;
        } else {
            clearError(pass);
        }

        if (isValid) {
            e.target.submit();
        }
    });
}

// --- KAYIT FORMU KONTROLÜ ---
if(registerForm) {
    registerForm.addEventListener('submit', function(e) {
        e.preventDefault();

        let isValid = true;
        const user = document.getElementById('reg-user');
        const email = document.getElementById('reg-email');
        const pass = document.getElementById('reg-pass');

        // Kullanıcı Adı Kontrolü
        if (user.value.trim() === '') {
            showError(user, 'Kullanıcı adı belirleyin.');
            isValid = false;
        } else {
            clearError(user);
        }

        // Email Regex Kontrolü
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(email.value)) {
            showError(email, 'Geçerli bir e-posta girin.');
            isValid = false;
        } else {
            clearError(email);
        }

        // Şifre Uzunluk Kontrolü
        if (pass.value.length < 6) {
            showError(pass, 'Şifre en az 6 karakter olmalı.');
            isValid = false;
        } else {
            clearError(pass);
        }

        if (isValid) {
            e.target.submit();
        }
    });
}