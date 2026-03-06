// collapsible.js

export function initCollapsible() {
    // Eksport funkcji do przestrzeni globalnej, by HTML (onclick) mógł z niej korzystać
    window.toggleSection = function(button) {
        const row = button.closest('.exercise-row');
        const collapsedInput = row.querySelector('input[name="collapsed"]');
        
        const isNowCollapsed = collapsedInput.value === "false";
        collapsedInput.value = isNowCollapsed ? "true" : "false";
        
        const icon = button.querySelector('i');
        if (icon) {
            icon.classList.toggle('bi-chevron-down', !isNowCollapsed);
            icon.classList.toggle('bi-chevron-right', isNowCollapsed);
        }
        
        refreshVisibility();

        if(window.autoSave) window.autoSave();
    };

    // Inicjalizacja przy starcie i przeładowaniach HTMX
    document.addEventListener('DOMContentLoaded', refreshVisibility);
    document.body.addEventListener('htmx:afterOnLoad', refreshVisibility);
}

function refreshVisibility() {
    const rows = Array.from(document.querySelectorAll('.exercise-row'));
    let hideLevel = 999;

    rows.forEach(row => {
        const levelInput = row.querySelector('input[name="level"]');
        const currentLevel = levelInput ? parseInt(levelInput.value) || 0 : 0;
        
        const collapsedInput = row.querySelector('input[name="collapsed"]');
        const isCollapsed = collapsedInput ? collapsedInput.value === "true" : false;

        if (currentLevel > 0 && currentLevel <= hideLevel) {
            hideLevel = 999;
        }

        if (hideLevel !== 999) {
            row.style.display = 'none';
        } else {
            row.style.display = ''; 
            row.querySelectorAll('textarea').forEach(ta => {
                ta.style.height = 'auto'; 
                if (ta.scrollHeight > 0) {
                    ta.style.height = ta.scrollHeight + 'px'; 
                }
            });
        }

        if (hideLevel === 999 && currentLevel > 0 && isCollapsed) {
            hideLevel = currentLevel;
        }
        
        if (currentLevel > 0) {
            row.classList.toggle('header-collapsed', isCollapsed);
        }
    });
}