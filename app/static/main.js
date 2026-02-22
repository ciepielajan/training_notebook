// app/static/main.js

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