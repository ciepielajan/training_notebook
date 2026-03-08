// collapsible.js

export function initCollapsible() {
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

    document.addEventListener('DOMContentLoaded', refreshVisibility);
    document.body.addEventListener('htmx:afterOnLoad', refreshVisibility);
}

function refreshVisibility() {
    const rows = Array.from(document.querySelectorAll('.exercise-row'));
    
    let hideLevel = 999;
    let currentHeader = null; // Śledzimy nagłówek, który aktualnie chowa elementy
    let hiddenCount = 0;      // Licznik ukrytych kart

    rows.forEach(row => {
        const levelInput = row.querySelector('input[name="level"]');
        const currentLevel = levelInput ? parseInt(levelInput.value) || 0 : 0;
        
        const collapsedInput = row.querySelector('input[name="collapsed"]');
        const isCollapsed = collapsedInput ? collapsedInput.value === "true" : false;

        // Reset: Jeśli trafiamy na nagłówek tego samego lub wyższego rzędu (np. zeszliśmy z H2 na nowe H2 lub na H1)
        if (currentLevel > 0 && currentLevel <= hideLevel) {
            if (currentHeader) {
                updateSummaryUI(currentHeader, hiddenCount);
            }
            hideLevel = 999;
            currentHeader = null;
            hiddenCount = 0;
        }

        // Ukrywanie elementów podrzędnych
        if (hideLevel !== 999) {
            row.style.display = 'none';
            hiddenCount++; // Zwiększamy licznik!
        } else {
            row.style.display = ''; 
            row.querySelectorAll('textarea').forEach(ta => {
                ta.style.height = 'auto'; 
                if (ta.scrollHeight > 0) {
                    ta.style.height = ta.scrollHeight + 'px'; 
                }
            });
            // Czyścimy UI licznika dla niezłożonych sekcji
            updateSummaryUI(row, 0);
        }

        // Start nowego ukrywania (kliknięto "Zwiń")
        if (hideLevel === 999 && currentLevel > 0 && isCollapsed) {
            hideLevel = currentLevel;
            currentHeader = row;
            hiddenCount = 0;
        }
        
        if (currentLevel > 0) {
            row.classList.toggle('header-collapsed', isCollapsed);
        }
    });

    // Zabezpieczenie dla ostatniego nagłówka na stronie (żeby też się zaktualizował po wyjściu z pętli)
    if (currentHeader) {
        updateSummaryUI(currentHeader, hiddenCount);
    }
}

// Funkcja pomocnicza do wstrzykiwania tekstu z licznikiem
function updateSummaryUI(row, count) {
    const summaryEl = row.querySelector('.collapse-summary');
    if (summaryEl) {
        if (count > 0) {
            // Jeśli są elementy, wyświetlamy ładny komunikat z ikonką
            summaryEl.innerHTML = `<i class="bi bi-card-list me-1"></i>Ukryto elementów: <strong>${count}</strong>`;
            summaryEl.style.display = 'block';
        } else {
            // Jeśli nie ma ukrytych kart pod nagłówkiem, chowamy licznik
            summaryEl.style.display = 'none';
        }
    }
}