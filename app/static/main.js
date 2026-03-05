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

    // 3. Konfiguracja Auto-Save
    const autoSave = debounce(() => {
        triggerSave('save', true);
    }, 1000);

    // a) Nasłuchiwanie na pisanie tekstu i klikanie checkboxów (to działało dobrze)
    document.body.addEventListener('input', (e) => {
        if (e.target.closest('#form')) autoSave();
    });
    document.body.addEventListener('change', (e) => {
        if (e.target.closest('#form')) autoSave();
    });

    // b) PANCERNE NASŁUCHIWANIE NA DODAWANIE I USUWANIE (MutationObserver)
    // To narzędzie patrzy na strukturę DOM. Jakikolwiek dodany lub usunięty HTML wyzwoli zapis.
    const formElement = document.getElementById('form');
    if (formElement) {
        const observer = new MutationObserver((mutations) => {
            let structureChanged = false;
            
            for (let mutation of mutations) {
                // Interesują nas tylko sytuacje, gdy dodano lub usunięto jakiś znacznik HTML
                if (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0) {
                    structureChanged = true;
                    break;
                }
            }
            
            if (structureChanged) {
                autoSave();
            }
        });

        // Odpalamy radar na formularzu: obserwuj dzieci (childList) i całe zagnieżdżenie (subtree)
        observer.observe(formElement, { childList: true, subtree: true });
    }
    
    window.autoSave = autoSave;
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
    
    if (triggerElement && triggerElement.classList.contains('nav-link') && triggerElement.hasAttribute('hx-get')) {
        document.querySelectorAll('.sidebar .nav-link').forEach(link => {
            link.classList.remove('active-workout');
        });
        triggerElement.classList.add('active-workout');
    }
});

// Dołączanie zaktualizowanego JSON-a do żądań HTMX
document.body.addEventListener('htmx:configRequest', function (evt) {
    if (evt.detail.path.includes('/card/repetition/')) {
        const rootElement = document.getElementById('fields-container');
        const structure = htmlTreeToJson(rootElement);
        evt.detail.parameters['json_body'] = JSON.stringify(structure);
    }
});


// --- Automatyczne dopasowanie wysokości pól tekstowych po ich załadowaniu ---
document.body.addEventListener('htmx:load', function(evt) {
    const textareas = evt.detail.elt.querySelectorAll('textarea');
    textareas.forEach(ta => {
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
    if (e.target.matches('.list-item-row input[type="text"]')) {
        const input = e.target;
        const currentRow = input.closest('.list-item-row');
        const listContainer = currentRow.closest('.list-items-container');

        // OBSŁUGA KLAWISZA ENTER
        if (e.key === 'Enter') {
            e.preventDefault(); 
            
            const newRow = currentRow.cloneNode(true);
            const newInput = newRow.querySelector('input[type="text"]');
            newInput.value = '';
            
            const checkbox = newRow.querySelector('input[type="checkbox"]');
            if (checkbox) checkbox.checked = false;

            currentRow.after(newRow);
            newInput.focus();

            // WYWOŁANIE ZAPISU PO DODANIU
            if(window.autoSave) window.autoSave();
        } 
        // OBSŁUGA KLAWISZA BACKSPACE
        else if (e.key === 'Backspace' && input.value === '') {
            if (listContainer.querySelectorAll('.list-item-row').length > 1) {
                e.preventDefault();
                
                const prevRow = currentRow.previousElementSibling;
                currentRow.remove(); 
                
                if (prevRow && prevRow.classList.contains('list-item-row')) {
                    const prevInput = prevRow.querySelector('input[type="text"]');
                    prevInput.focus();
                    
                    const val = prevInput.value;
                    prevInput.value = '';
                    prevInput.value = val;
                }

                // WYWOŁANIE ZAPISU PO USUNIĘCIU
                if(window.autoSave) window.autoSave();
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
    
    const isNowCollapsed = collapsedInput.value === "false";
    collapsedInput.value = isNowCollapsed ? "true" : "false";
    
    const icon = button.querySelector('i');
    if (icon) {
        icon.classList.toggle('bi-chevron-down', !isNowCollapsed);
        icon.classList.toggle('bi-chevron-right', isNowCollapsed);
    }
    
    refreshVisibility();

    // WYWOŁANIE ZAPISU PO ZWINIĘCIU/ROZWINIĘCIU (opcjonalne, ale polecane)
    if(window.autoSave) window.autoSave();
}

function refreshVisibility() {
    const rows = Array.from(document.querySelectorAll('.exercise-row'));
    let hideLevel = 999;

    rows.forEach(row => {
        const levelInput = row.querySelector('input[name="level"]');
        const currentLevel = levelInput ? parseInt(levelInput.value) || 0 : 0;
        
        const collapsedInput = row.querySelector('input[name="collapsed"]');
        const isCollapsed = collapsedInput ? collapsedInput.value === "true" : false;

        if (currentLevel > 0 && currentLevel <= hideLevel) {
            hideLevel = 999;
        }

        if (hideLevel !== 999) {
            row.style.display = 'none';
        } else {
            row.style.display = ''; 
            
            row.querySelectorAll('textarea').forEach(ta => {
                ta.style.height = 'auto'; 
                if (ta.scrollHeight > 0) {
                    ta.style.height = ta.scrollHeight + 'px'; 
                }
            });
        }

        if (hideLevel === 999 && currentLevel > 0 && isCollapsed) {
            hideLevel = currentLevel;
        }
        
        if (currentLevel > 0) {
            row.classList.toggle('header-collapsed', isCollapsed);
        }
    });
}

document.addEventListener('DOMContentLoaded', refreshVisibility);
document.body.addEventListener('htmx:afterOnLoad', refreshVisibility);