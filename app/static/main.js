// main.js
import { initSidebar } from './ui.js';
import { initImportExport } from './import_export.js';
import { triggerSave, debounce, htmlTreeToJson } from './storage.js';
import { initCollapsible } from './collapsible.js';
import { initLists } from './lists.js';

// Eksponowanie funkcji dla atrybutów HTML (onclick="") oraz eventów HTMX
window.triggerSave = triggerSave;
window.htmlTreeToJson = htmlTreeToJson;

document.addEventListener('DOMContentLoaded', function() {
    // 1. Inicjalizacja modułów UI
    initSidebar();
    initImportExport();
    initCollapsible();
    initLists();

    // 2. Podpięcie przycisków ręcznych dla zapisu i eksportu
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
    window.autoSave = autoSave;

    // a) Nasłuchiwanie na pisanie tekstu i klikanie checkboxów
    document.body.addEventListener('input', (e) => {
        if (e.target.closest('#form')) autoSave();
    });
    document.body.addEventListener('change', (e) => {
        if (e.target.closest('#form')) autoSave();
    });

    // b) Nasłuchiwanie na dodawanie i usuwanie bloków DOM
    const formElement = document.getElementById('form');
    if (formElement) {
        const observer = new MutationObserver((mutations) => {
            let structureChanged = false;
            for (let mutation of mutations) {
                if (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0) {
                    structureChanged = true;
                    break;
                }
            }
            if (structureChanged) autoSave();
        });
        observer.observe(formElement, { childList: true, subtree: true });
    }
});


// ==========================================
// HTMX: Konfiguracja i zdarzenia globalne
// ==========================================

// Wyróżnianie aktywnego treningu w menu
document.body.addEventListener('htmx:afterOnLoad', function(evt) {
    const triggerElement = evt.detail.elt;
    if (triggerElement && triggerElement.classList.contains('nav-link') && triggerElement.hasAttribute('hx-get')) {
        document.querySelectorAll('.sidebar .nav-link').forEach(link => {
            link.classList.remove('active-workout');
        });
        triggerElement.classList.add('active-workout');
    }
});

// Dołączanie zaktualizowanego JSON-a do żądań HTMX (np. powielanie treningu)
document.body.addEventListener('htmx:configRequest', function (evt) {
    if (evt.detail.path.includes('/card/repetition/')) {
        const rootElement = document.getElementById('form');
        const structure = htmlTreeToJson(rootElement);
        evt.detail.parameters['json_body'] = JSON.stringify(structure);
    }
});

// Automatyczne dopasowanie wysokości pól tekstowych (notes.html) po wczytaniu
document.body.addEventListener('htmx:load', function(evt) {
    const textareas = evt.detail.elt.querySelectorAll('textarea');
    textareas.forEach(ta => {
        if (ta.value.trim() !== '') {
            ta.style.height = ''; 
            ta.style.height = ta.scrollHeight + 'px';
        }
    });
});