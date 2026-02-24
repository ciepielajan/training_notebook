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
                if (input.type === 'checkbox') {
                    data[input.name] = input.checked;
                } else {
                    data[input.name] = input.value;
                }
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
                // Jeśli zapisaliśmy "Nowy trening",
                // powstał nowy plik na dysku, więc musimy odświeżyć listę w menu
                if (isNewFile) {
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


// --- Automatyczne dopasowanie wysokości pól tekstowych po ich załadowaniu ---
document.body.addEventListener('htmx:load', function(evt) {
    // evt.detail.elt to kontener, który właśnie wyrenderował HTMX (albo cały dokument na starcie)
    // Szukamy w nim wszystkich pól textarea
    const textareas = evt.detail.elt.querySelectorAll('textarea');
    
    textareas.forEach(ta => {
        // Jeśli textarea ma jakąś zawartość, natychmiast przeliczamy jego wysokość
        if (ta.value.trim() !== '') {
            ta.style.height = ''; 
            ta.style.height = ta.scrollHeight + 'px';
        }
    });
});

// ==========================================
// 4. UX LISTY (Enter i Backspace jak w MS Word)
// ==========================================
document.addEventListener('keydown', function(e) {
    // Sprawdzamy, czy wciskamy klawisz będąc w inpucie na liście
    if (e.target.matches('.list-item-row input[type="text"]')) {
        const input = e.target;
        const currentRow = input.closest('.list-item-row');
        const listContainer = currentRow.closest('.list-items-container');

        // OBSŁUGA KLAWISZA ENTER (Tworzenie nowego punktu)
        if (e.key === 'Enter') {
            e.preventDefault(); // Blokujemy przypadkowy submit formularza
            
            // Klonujemy węzeł zachowując strukturę HTML
            const newRow = currentRow.cloneNode(true);
            
            // Czyścimy dane w klonie
            const newInput = newRow.querySelector('input[type="text"]');
            newInput.value = '';
            
            const checkbox = newRow.querySelector('input[type="checkbox"]');
            if (checkbox) checkbox.checked = false;

            // Wstawiamy po obecnym elemencie i przerzucamy tam kursor
            currentRow.after(newRow);
            newInput.focus();
        } 
        // OBSŁUGA KLAWISZA BACKSPACE (Usuwanie punktu, jeśli jest pusty)
        else if (e.key === 'Backspace' && input.value === '') {
            // Zabezpieczenie: Zawsze zostawiamy chociaż 1 punkt na liście
            if (listContainer.querySelectorAll('.list-item-row').length > 1) {
                e.preventDefault();
                
                const prevRow = currentRow.previousElementSibling;
                currentRow.remove(); // Usuwamy bieżący pusty rząd
                
                // Przenosimy kursor na poprzedni punkt i ustawiamy na końcu jego tekstu
                if (prevRow && prevRow.classList.contains('list-item-row')) {
                    const prevInput = prevRow.querySelector('input[type="text"]');
                    prevInput.focus();
                    
                    // Trick wymuszający kursor na końcu tekstu
                    const val = prevInput.value;
                    prevInput.value = '';
                    prevInput.value = val;
                }
            }
        }
    }
});


// ==========================================
// ZARZĄDZANIE WIDOCZNOŚCIĄ SEKCJI (ZAGNIEDŻDZENIA H1-H4)
// ==========================================

function toggleSection(button) {
    const row = button.closest('.exercise-row');
    const collapsedInput = row.querySelector('input[name="collapsed"]');
    
    // 1. Zmiana stanu w ukrytym polu (dzięki temu htmlTreeToJson to zapisze)
    const isNowCollapsed = collapsedInput.value === "false";
    collapsedInput.value = isNowCollapsed ? "true" : "false";
    
    // 2. Opcjonalna animacja ikony
    const icon = button.querySelector('i');
    if (icon) {
        icon.classList.toggle('bi-chevron-down', !isNowCollapsed);
        icon.classList.toggle('bi-chevron-right', isNowCollapsed);
    }
    
    // 3. Przeliczenie widoczności
    refreshVisibility();
}

function refreshVisibility() {
    const rows = Array.from(document.querySelectorAll('.exercise-row'));
    
    // hideLevel przechowuje poziom nagłówka, który aktualnie ukrywa elementy pod sobą
    // Wartość 999 oznacza brak ukrywania
    let hideLevel = 999;

    rows.forEach(row => {
        const levelInput = row.querySelector('input[name="level"]');
        const currentLevel = levelInput ? parseInt(levelInput.value) || 0 : 0;
        
        const collapsedInput = row.querySelector('input[name="collapsed"]');
        const isCollapsed = collapsedInput ? collapsedInput.value === "true" : false;

        // Jeśli napotkaliśmy na nagłówek, który jest równy lub "wyższy" (mniejsza liczba)
        // niż poziom, który wymusił ukrywanie, to musimy przerwać ukrywanie
        if (currentLevel > 0 && currentLevel <= hideLevel) {
            hideLevel = 999;
        }

        // Zastosowanie widoczności: 
        // Wszystko co trafia pod aktywny hideLevel (poza nowymi nadrzędnymi nagłówkami) znika
        if (hideLevel !== 999) {
            row.style.display = 'none';
        } else {
            row.style.display = ''; // Odkrywamy z powrotem
            
            // --- FIX DLA TEXTAREA (Przywracanie wysokości po rozwinięciu) ---
            // Ponieważ element był ukryty (display: none), przeglądarka wyzerowała jego scrollHeight.
            // Wymuszamy ponowne przeliczenie wysokości, gdy znów jest widoczny.
            row.querySelectorAll('textarea').forEach(ta => {
                ta.style.height = 'auto'; // Reset wysokości
                if (ta.scrollHeight > 0) {
                    ta.style.height = ta.scrollHeight + 'px'; // Dopasowanie do zawartości
                }
            });
        }

        // Jeśli sam ten wiersz jest nagłówkiem, nie jest aktualnie przez nikogo ukryty, 
        // a ma status 'collapsed', to on zaczyna ukrywać wszystko pod sobą
        if (hideLevel === 999 && currentLevel > 0 && isCollapsed) {
            hideLevel = currentLevel;
        }
        
        // Dodanie subtelnej klasy CSS dla zwiniętego nagłówka (jeśli chcesz mieć kreskę)
        if (currentLevel > 0) {
            row.classList.toggle('header-collapsed', isCollapsed);
        }
    });
}

// Uruchamiamy po załadowaniu całej strony (aby obsłużyć dane z JSON-a)
document.addEventListener('DOMContentLoaded', refreshVisibility);

// Uruchamiamy również gdy HTMX wczyta nowy trening, doda nowy nagłówek lub cokolwiek zmieni
document.body.addEventListener('htmx:afterOnLoad', refreshVisibility);