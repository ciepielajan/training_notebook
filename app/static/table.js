// app/static/table.js
export function initTable() {
    window.selectItem = function(buttonElement, itemId, itemName) {
        const container = buttonElement.closest('.dropdown');
        
        // Zaktualizuj ukryte pola
        container.querySelector('.item-value-input').value = itemName;
        container.querySelector('.item-id-input').value = itemId;
        
        // Zaktualizuj etykietę na przycisku
        container.querySelector('.item-name').textContent = itemName;
        
        // Wymuś auto-zapis
        if (typeof window.autoSave === 'function') {
            window.autoSave();
        }
    };
}