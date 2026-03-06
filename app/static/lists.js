// lists.js

export function initLists() {
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

                    if(window.autoSave) window.autoSave();
                }
            }
        }
    });
}