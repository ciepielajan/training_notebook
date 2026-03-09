// storage.js

// 1. Parsowanie HTML do struktury JSON
export function htmlTreeToJson(element) {
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
            const childData = htmlTreeToJson(node);
                
            // Oddzielamy zdefiniowane kolekcje (jak nagłówek) od ogólnej listy kart (items)
            if (node.dataset.arrayName) {
                data[node.dataset.arrayName] = childData[node.dataset.childrenKey || 'items'] || [];
            } else {
                items.push(childData);
            }
        }
    });

    if (items.length > 0) {
        let keyName = element.dataset.childrenKey || 'items';
        data[keyName] = items;
    }

    return data;
}

// 2. Główna funkcja zapisu
export async function triggerSave(actionType, isAutoSave = false) {
    const mainContainer = document.getElementById('form');
    if (!mainContainer) return;

    // Budujemy JSON z naszej struktury
    const structure = htmlTreeToJson(mainContainer); 
    const jsonString = JSON.stringify(structure);
    
    // Szukamy inputa z nazwą pliku
    const filenameInput = document.querySelector('input[name="current_filename"]');
    const currentFilename = filenameInput ? filenameInput.value : '';

    // ==============================================
    // OPCJA A: EKSPORT (Pobieranie pliku w oknie)
    // ==============================================
    if (actionType === 'export') {
        // Tworzymy wirtualny formularz tylko po to, by pobrać plik (wymaga przeładowania okna do zapisu)
        const tempForm = document.createElement('form');
        tempForm.method = 'POST';
        tempForm.action = '/export';
        
        const inputJson = document.createElement('input');
        inputJson.type = 'hidden';
        inputJson.name = 'json_body';
        inputJson.value = jsonString;
        tempForm.appendChild(inputJson);

        const inputName = document.createElement('input');
        inputName.type = 'hidden';
        inputName.name = 'current_filename';
        inputName.value = currentFilename;
        tempForm.appendChild(inputName);

        document.body.appendChild(tempForm);
        tempForm.submit();
        document.body.removeChild(tempForm);
        return;
    }

    // ==============================================
    // OPCJA B: ZAPIS (Auto-save lub Ręczny)
    // ==============================================
    const saveBtn = document.getElementById('sidebar-save-btn');
    const defaultBtnHtml = '<i class="bi bi-floppy"></i> <span class="menu-text">Zapisz</span>';
    
    if (saveBtn && !isAutoSave) {
        saveBtn.innerHTML = '<i class="bi bi-hourglass-split spin-icon"></i> <span class="menu-text">Zapisywanie...</span>';
    }

    try {
        // Ręcznie tworzymy ładunek z danymi
        const formData = new FormData();
        formData.append('json_body', jsonString);
        formData.append('current_filename', currentFilename);

        const response = await fetch('/save', { method: 'POST', body: formData });
        
        if (!response.ok) throw new Error("Błąd serwera: " + response.status);
        if (response.status === 204) return;

        const text = await response.text();
        if (text) {
            const result = JSON.parse(text);
            if (result.filename && filenameInput) {
                filenameInput.value = result.filename;
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

// 3. Funkcja opóźniająca
export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}