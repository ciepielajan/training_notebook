// app/static/main.js

// ==========================================
// 1. FUNKCJE POMOCNICZE
// ==========================================

// Obsługa parsowania HTML do struktury JSON
function htmlTreeToJson(element) {
    let data = {};
    let items = [];

    const allInputs = element.querySelectorAll('input, select, textarea');
    allInputs.forEach(input => {
        const ownerNode = input.closest('.node');
        if (ownerNode === element) {
            if (input.name && input.name !== 'json_body') {
                data[input.name] = input.value;
            }
        }
    });

    const allNodes = element.querySelectorAll('.node');
    allNodes.forEach(node => {
        const parentNode = node.parentElement.closest('.node');
        if (parentNode === element) {
            items.push(htmlTreeToJson(node));
        }
    });

    if (items.length > 0) {
        let keyName = element.dataset.childrenKey || 'items';
        data[keyName] = items;
    }

    return data;
}


// ==========================================
// 2. INICJALIZACJA APLIKACJI (po załadowaniu DOM)
// ==========================================
document.addEventListener('DOMContentLoaded', function() {

    // --- Obsługa HAMBURGERA (zwijanie/rozwijanie z pamięcią localStorage) ---
    const sidebar = document.getElementById('sidebar');
    const hamburgerBtn = document.getElementById('hamburger-btn');
    
    // 1. Przy starcie strony sprawdzamy, co przeglądarka zapamiętała
    if (localStorage.getItem('sidebarState') === 'open') {
        sidebar.classList.remove('collapsed');
    } else if (localStorage.getItem('sidebarState') === 'closed') {
        sidebar.classList.add('collapsed');
    }

    if (hamburgerBtn && sidebar) {
        hamburgerBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            
            // 2. Zapisujemy decyzję użytkownika po każdym kliknięciu
            if (sidebar.classList.contains('collapsed')) {
                localStorage.setItem('sidebarState', 'closed');
            } else {
                localStorage.setItem('sidebarState', 'open');
            }
        });
    }

    // --- Obsługa przycisku IMPORT z menu bocznego ---
    const importBtn = document.getElementById('sidebar-import-btn');
    const fileInput = document.getElementById('sidebar-file-input');
    const submitBtn = document.getElementById('sidebar-submit-btn');

    if (importBtn && fileInput && submitBtn) {
        importBtn.addEventListener('click', function(e) {
            e.preventDefault();
            fileInput.click(); // Otwiera okno wyboru pliku
        });

        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                submitBtn.click(); // Automatycznie wysyła ukryty formularz HTMX
            }
        });
    }

    // --- Obsługa akcji ZAPISU (Zapisz, Zapisz jako, Eksportuj) ---
    const mainForm = document.getElementById('form');
    const saveActionInput = document.getElementById('hidden-save-action');

    function triggerSave(actionType) {
        if (!mainForm || !saveActionInput) return;

        saveActionInput.value = actionType;

        // 1. Zawsze najpierw zbieramy najnowsze dane do ukrytego inputa
        const rootElement = document.getElementById('fields-container');
        const structure = htmlTreeToJson(rootElement);
        document.getElementById('hidden-json-input').value = JSON.stringify(structure);

        // 2. Eksport pobiera plik, więc wymusza standardowe pobieranie (nie przeładowuje to strony)
        if (actionType === 'export') {
            mainForm.submit();
        } else {
            // 3. Zapisz / Zapisz Jako - wysyłamy plik "po cichu" w TLE
            const formData = new FormData(mainForm);
            const isNewFile = !formData.get('current_filename'); // Czy to czysty, nowy trening?

            fetch('/save', {
                method: 'POST',
                body: formData
            }).then(response => {
                // Jeśli kliknęliśmy "Zapisz jako" lub zapisaliśmy "Nowy trening",
                // powstał nowy plik na dysku, więc musimy odświeżyć listę w menu
                if (actionType === 'save_as' || isNewFile) {
                    window.location.reload();
                } else {
                    // ZWYKŁY ZAPIS - BRAK PRZEŁADOWANIA! 🎉
                    // Dajemy tylko ładny efekt wizualny na przycisku
                    const saveBtn = document.getElementById('sidebar-save-btn');
                    if (saveBtn) {
                        const originalHtml = saveBtn.innerHTML;
                        saveBtn.innerHTML = '<i class="bi bi-check-lg"></i> <span class="menu-text">Zapisano!</span>';
                        setTimeout(() => {
                            saveBtn.innerHTML = originalHtml;
                        }, 2000);
                    }
                }
            }).catch(error => {
                alert("Wystąpił błąd podczas zapisu!");
            });
        }
    }

    document.getElementById('sidebar-save-btn')?.addEventListener('click', (e) => { 
        e.preventDefault(); triggerSave('save'); 
    });

    document.getElementById('sidebar-save-as-btn')?.addEventListener('click', (e) => { 
        e.preventDefault(); triggerSave('save_as'); 
    });

    document.getElementById('sidebar-export-btn')?.addEventListener('click', (e) => { 
        e.preventDefault(); triggerSave('export'); 
    });

    // --- GŁÓWNE ZDARZENIE FORMULARZA: Budowanie JSON-a przed wysłaniem ---
    if (mainForm) {
        mainForm.addEventListener('submit', function (e) {
            const rootElement = document.getElementById('fields-container');
            const structure = htmlTreeToJson(rootElement);
            document.getElementById('hidden-json-input').value = JSON.stringify(structure);
            
            // Dla pewności wypisujemy wysyłany json w konsoli
            console.log("WYSYŁANY JSON:", JSON.stringify(structure, null, 2));
        });
    }

});


// ==========================================
// 3. SPECJALNA OBSŁUGA HTMX
// ==========================================

// --- Wyróżnianie aktywnego treningu w menu ---
document.body.addEventListener('htmx:afterOnLoad', function(evt) {
    const triggerElement = evt.detail.elt;
    
    // Sprawdzamy, czy element, który wywołał załadowanie HTMX, to link z naszego menu bocznego
    if (triggerElement && triggerElement.classList.contains('nav-link') && triggerElement.hasAttribute('hx-get')) {
        
        // Usuwamy klasę aktywną ze wszystkich linków w pasku
        document.querySelectorAll('.sidebar .nav-link').forEach(link => {
            link.classList.remove('active-workout');
        });
        
        // Nadajemy klasę aktywną tylko temu, w który właśnie kliknęliśmy
        triggerElement.classList.add('active-workout');
    }
});

// Dołączanie zaktualizowanego JSON-a do żądań HTMX (np. zmiana rodzaju powtórzeń)
document.body.addEventListener('htmx:configRequest', function (evt) {
    if (evt.detail.path.includes('/card/repetition/')) {
        const rootElement = document.getElementById('fields-container');
        const structure = htmlTreeToJson(rootElement);
        evt.detail.parameters['json_body'] = JSON.stringify(structure);
    }
});

