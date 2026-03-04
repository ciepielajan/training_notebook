// main.js

import { initSidebar } from './ui.js';
import { initImportExport } from './import_export.js';
import { triggerSave, debounce } from './storage.js';

document.addEventListener('DOMContentLoaded', function() {
    // 1. Inicjalizacja UI
    initSidebar();
    initImportExport();

    // 2. Podpięcie przycisków ręcznych
    document.getElementById('sidebar-save-btn')?.addEventListener('click', (e) => { 
        e.preventDefault(); 
        triggerSave('save', false); 
    });

    document.getElementById('sidebar-export-btn')?.addEventListener('click', (e) => { 
        e.preventDefault(); 
        triggerSave('export', false); 
    });

    // 3. Konfiguracja Auto-Save (MOCNO ODCHUDZONA)
    const autoSave = debounce(() => {
        // Wszystko co robimy, to po prostu wywołujemy zapis po 2 sekundach bezczynności.
        // Koniec z nadawaniem nazw po stronie JS!
        triggerSave('save', true);
    }, 2000);

    // PANCERNE NASŁUCHIWANIE
    document.body.addEventListener('input', (e) => {
        // ZMIANA: Nasłuchujemy zmian w CAŁYM formularzu (nagłówek + karty)
        if (e.target.closest('#form')) {
            autoSave();
        }
    });

    document.body.addEventListener('change', (e) => {
        // ZMIANA: Podobnie tutaj
        if (e.target.closest('#form')) {
            autoSave();
        }
    });
});




// ==========================================
// 2. FUNKCJE POMOCNICZE
// ==========================================

// Obsługa parsowania HTML do struktury JSON
window.htmlTreeToJson = function htmlTreeToJson(element) {
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

// Dołączanie zaktualizowanego JSON-a do żądań HTMX (np. zmiana rodzaju powtórzeń lub duplikacja)
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
// 5. ZARZĄDZANIE WIDOCZNOŚCIĄ SEKCJI (ZAGNIEDŻDZENIA H1-H4)
// ==========================================

window.toggleSection = function(button) {
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
        
        // Dodanie subtelnej klasy CSS dla zwiniętego nagłówka
        if (currentLevel > 0) {
            row.classList.toggle('header-collapsed', isCollapsed);
        }
    });
}

// Uruchamiamy po załadowaniu całej strony (aby obsłużyć dane z JSON-a)
document.addEventListener('DOMContentLoaded', refreshVisibility);

// Uruchamiamy również gdy HTMX wczyta nowy trening, doda nowy nagłówek lub cokolwiek zmieni
document.body.addEventListener('htmx:afterOnLoad', refreshVisibility);