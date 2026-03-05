// storage.js

// Główna funkcja zapisu
export async function triggerSave(actionType, isAutoSave = false) {
    const mainForm = document.getElementById('form');
    const saveActionInput = document.getElementById('hidden-save-action');
    if (!mainForm || !saveActionInput) return;

    saveActionInput.value = actionType;

    // 1. Zbieramy aktualną strukturę z DOM za pomocą Twojej funkcji
    const structure = window.htmlTreeToJson(mainForm); 
    document.getElementById('hidden-json-input').value = JSON.stringify(structure);

    // 2. Eksport przez klasyczny formularz
    if (actionType === 'export') {
        mainForm.action = '/export'; // <--- DODAJ TO: Wskazujemy nowy endpoint
        mainForm.method = 'POST';    // <--- DODAJ TO: Wymuszamy metodę POST
        mainForm.submit();
        return;
    }

    // 3. UI Feedback (Tylko dla ręcznego zapisu)
    const saveBtn = document.getElementById('sidebar-save-btn');
    const defaultBtnHtml = '<i class="bi bi-floppy"></i> <span class="menu-text">Zapisz</span>';
    
    if (saveBtn && !isAutoSave) {
        saveBtn.innerHTML = '<i class="bi bi-hourglass-split spin-icon"></i> <span class="menu-text">Zapisywanie...</span>';
    }

    // 4. Wysłanie danych do serwera (Fetch)
    try {
        const formData = new FormData(mainForm);
        const response = await fetch('/save', { method: 'POST', body: formData });
        
        if (!response.ok) throw new Error("Błąd serwera: " + response.status);
        
        // Pomińmy obsługę UI dla statusu 204 (Auto-zapis)
        if (response.status === 204) return;

        // Jeśli endpoint zwróci JSON (dla ręcznego zapisu)
        const text = await response.text();
        if (text) {
            const result = JSON.parse(text);
            if (result.filename) {
                document.querySelector('input[name="current_filename"]').value = result.filename;
            }
        }
       
        if (saveBtn && !isAutoSave) {
            saveBtn.innerHTML = '<i class="bi bi-check-lg text-success"></i> <span class="menu-text text-success">Zapisano!</span>';
            setTimeout(() => { saveBtn.innerHTML = defaultBtnHtml; }, 2000);
        }

    } catch (error) {
        console.error("Błąd podczas zapisu:", error);
        if (saveBtn && !isAutoSave) {
            saveBtn.innerHTML = '<i class="bi bi-x-circle text-danger"></i> <span class="menu-text text-danger">Błąd!</span>';
            setTimeout(() => { saveBtn.innerHTML = defaultBtnHtml; }, 3000);
        }
    }
}

// Funkcja opóźniająca wywołanie (absolutnie niezbędna do auto-save!)
export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}