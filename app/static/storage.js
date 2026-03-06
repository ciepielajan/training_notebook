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
            items.push(htmlTreeToJson(node));
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
    const mainForm = document.getElementById('form');
    const saveActionInput = document.getElementById('hidden-save-action');
    if (!mainForm || !saveActionInput) return;

    saveActionInput.value = actionType;

    const structure = htmlTreeToJson(mainForm); 
    document.getElementById('hidden-json-input').value = JSON.stringify(structure);

    if (actionType === 'export') {
        mainForm.action = '/export'; 
        mainForm.method = 'POST';    
        mainForm.submit();
        return;
    }

    const saveBtn = document.getElementById('sidebar-save-btn');
    const defaultBtnHtml = '<i class="bi bi-floppy"></i> <span class="menu-text">Zapisz</span>';
    
    if (saveBtn && !isAutoSave) {
        saveBtn.innerHTML = '<i class="bi bi-hourglass-split spin-icon"></i> <span class="menu-text">Zapisywanie...</span>';
    }

    try {
        const formData = new FormData(mainForm);
        const response = await fetch('/save', { method: 'POST', body: formData });
        
        if (!response.ok) throw new Error("Błąd serwera: " + response.status);
        if (response.status === 204) return;

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

// 3. Funkcja opóźniająca (Auto-Save)
export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}