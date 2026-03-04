// storage.js

// Główna funkcja zapisu
export async function triggerSave(actionType, isAutoSave = false) {
    const mainForm = document.getElementById('form');
    const saveActionInput = document.getElementById('hidden-save-action');
    if (!mainForm || !saveActionInput) return;

    saveActionInput.value = actionType;

    // Budowanie JSON
    const rootElement = document.getElementById('fields-container');
    // Używamy window. dla pewności, że moduł widzi funkcję z main.js
    const structure = window.htmlTreeToJson(rootElement); 
    document.getElementById('hidden-json-input').value = JSON.stringify(structure);

    // Eksport obsługujemy klasycznie przez submit (pobieranie pliku)
    if (actionType === 'export') {
        mainForm.submit();
        return;
    }

    const formData = new FormData(mainForm);
    const saveBtn = document.getElementById('sidebar-save-btn');
    const defaultBtnHtml = '<i class="bi bi-floppy"></i> <span class="menu-text">Zapisz</span>';

    // UI Feedback
    if (saveBtn) {
        saveBtn.innerHTML = isAutoSave 
            ? '<i class="bi bi-arrow-repeat spin-icon"></i> <span class="menu-text">Auto-zapis...</span>'
            : '<i class="bi bi-hourglass-split spin-icon"></i> <span class="menu-text">Zapisywanie...</span>';
    }

    try {
        const response = await fetch('/save', { method: 'POST', body: formData });
        
        if (!response.ok) throw new Error("Błąd serwera: " + response.status);
        
        // Bezpieczne parsowanie JSON (zapobiega błędowi Unexpected end of input)
        const text = await response.text();
        if (!text) throw new Error("Pusta odpowiedź z serwera");
        const result = JSON.parse(text);

        // Zawsze aktualizujemy pole nazwy (źródło prawdy z serwera)
        if (result.filename) {
            document.querySelector('input[name="current_filename"]').value = result.filename;
        }
       
        // Feedback sukcesu
        if (saveBtn) {
            saveBtn.innerHTML = '<i class="bi bi-check-lg text-success"></i> <span class="menu-text text-success">Zapisano!</span>';
            setTimeout(() => { 
                // Przywracamy domyślny wygląd tylko jeśli w międzyczasie nie odpalił się kolejny auto-zapis
                if (!saveBtn.innerHTML.includes('spin-icon')) {
                    saveBtn.innerHTML = defaultBtnHtml; 
                }
            }, 2000);
        }

    } catch (error) {
        console.error("Błąd podczas zapisu:", error);
        if (saveBtn) {
            saveBtn.innerHTML = '<i class="bi bi-x-circle text-danger"></i> <span class="menu-text text-danger">Błąd!</span>';
            setTimeout(() => { saveBtn.innerHTML = defaultBtnHtml; }, 3000);
        }
    }
}

export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}