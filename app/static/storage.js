// storage.js

// Funkcja formatująca datę (z naszej poprzedniej rozmowy)
export function getFormattedTimestamp() {
    const now = new Date();
    const yy = String(now.getFullYear()).slice(-2);
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const hh = String(now.getHours()).padStart(2, '0');
    const min = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    return `${yy}${mm}${dd}${hh}${min}${ss}`;
}

// Główna funkcja zapisu
export async function triggerSave(actionType, isAutoSave = false, isNewlyGenerated = false) {
    const mainForm = document.getElementById('form');
    const saveActionInput = document.getElementById('hidden-save-action');
    if (!mainForm || !saveActionInput) return;

    saveActionInput.value = actionType;

    // Budowanie JSON (Zakładam, że funkcja htmlTreeToJson jest dostępna globalnie)
    const rootElement = document.getElementById('fields-container');
    const structure = htmlTreeToJson(rootElement);
    document.getElementById('hidden-json-input').value = JSON.stringify(structure);

    if (actionType === 'export') {
        mainForm.submit();
        return;
    }

    const formData = new FormData(mainForm);
    const isNewFile = !formData.get('current_filename') || 
                      formData.get('current_filename').trim() === '' || 
                      isNewlyGenerated;
    const saveBtn = document.getElementById('sidebar-save-btn');
    const defaultBtnHtml = '<i class="bi bi-floppy"></i> <span class="menu-text">Zapisz</span>';

    if (saveBtn) {
        saveBtn.innerHTML = isAutoSave 
            ? '<i class="bi bi-arrow-repeat spin-icon"></i> <span class="menu-text">Auto-zapis...</span>'
            : '<i class="bi bi-hourglass-split spin-icon"></i> <span class="menu-text">Zapisywanie...</span>';
    }

    try {
        const response = await fetch('/save', { method: 'POST', body: formData });
        if (!response.ok) throw new Error("Błąd serwera: " + response.status);
        
        const result = await response.json(); // Oczekujemy JSON-a z serwera!

        // Aktualizujemy ukryte pole w HTML, żeby kolejny auto-zapis wiedział, na czym pracuje
        if (result.filename) {
            document.querySelector('input[name="current_filename"]').value = result.filename;
        }

        if (isNewFile) {
            // =====================================
            // KROK 4: Pancerne wywołanie HTMX
            // =====================================
            console.log("🔥 KROK 4: Wysyłam sygnał do HTMX o odświeżenie listy!");
            
            // Najbezpieczniejsza metoda: użycie wbudowanej funkcji HTMX
            if (typeof htmx !== 'undefined') {
                htmx.trigger("body", "updateSidebar");
            } else {
                // Metoda zapasowa z wymuszonym "bąbelkowaniem"
                document.body.dispatchEvent(new CustomEvent("updateSidebar", { bubbles: true }));
            }
        }
        
        // Feedback dla użytkownika
        if (saveBtn) {
            saveBtn.innerHTML = '<i class="bi bi-check-lg text-success"></i> <span class="menu-text text-success">Zapisano!</span>';
            setTimeout(() => { saveBtn.innerHTML = defaultBtnHtml; }, 2000);
        }

    } catch (error) {
        console.error("Błąd podczas zapisu:", error);
        if (saveBtn) {
            saveBtn.innerHTML = '<i class="bi bi-x-circle text-danger"></i> <span class="menu-text text-danger">Błąd!</span>';
            setTimeout(() => { saveBtn.innerHTML = defaultBtnHtml; }, 3000);
        }
    }
}

// Funkcja debouncing dla Auto-Save
export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}