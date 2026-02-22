// app/static/main.js

document.addEventListener('DOMContentLoaded', function() {
    
    // --- Obsługa przycisku IMPORT z menu bocznego ---
    const importBtn = document.getElementById('sidebar-import-btn');
    const fileInput = document.getElementById('sidebar-file-input');
    const submitBtn = document.getElementById('sidebar-submit-btn');

    if (importBtn && fileInput && submitBtn) {
        // Kliknięcie w link otwiera systemowe okno wyboru pliku
        importBtn.addEventListener('click', function(e) {
            e.preventDefault();
            fileInput.click(); 
        });

        // Kiedy użytkownik wybierze plik, automatycznie klikamy ukryty przycisk wywołując HTMX
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                submitBtn.click();
            }
        });
    }

    // --- Obsługa przycisku ZAPISZ z menu bocznego ---
    const saveBtn = document.getElementById('sidebar-save-btn');
    const mainForm = document.getElementById('form');

    if (saveBtn && mainForm) {
        saveBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // Wywołuje natywne wysłanie głównego formularza (uruchomi Twój skrypt json_body)
            mainForm.requestSubmit(); 
        });
    }

});


// 1. Obsługa zwijania/rozwijania paska bocznego
document.addEventListener('DOMContentLoaded', function() {
    const hamburgerBtn = document.getElementById('hamburger-btn');
    if (hamburgerBtn) {
        hamburgerBtn.addEventListener('click', function() {
            document.getElementById('sidebar').classList.toggle('collapsed');
        });
    }
});

// 2. Obsługa parsowania HTML do JSON
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

// 3. Obsługa zapisu (Submit formularza)
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('form');
    if (form) {
        form.addEventListener('submit', function (e) {
            const rootElement = document.getElementById('fields-container');
            const structure = htmlTreeToJson(rootElement);
            const jsonString = JSON.stringify(structure);
            document.getElementById('hidden-json-input').value = jsonString;
            console.log("WYGENEROWANY JSON:", JSON.stringify(structure, null, 2));
        });
    }
});

// 4. HTMX - Dołączanie JSON-a przy zapytaniach
document.body.addEventListener('htmx:configRequest', function (evt) {
    if (evt.detail.path.includes('/card/repetition/')) {
        const rootElement = document.getElementById('fields-container');
        const structure = htmlTreeToJson(rootElement);
        evt.detail.parameters['json_body'] = JSON.stringify(structure);
    }
});