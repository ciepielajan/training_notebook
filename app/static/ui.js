// ui.js
export function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const hamburgerBtn = document.getElementById('hamburger-btn');
    
    let savedState = null;
    try {
        // Przeglądarka może zablokować tę linię - musimy to przechwycić
        savedState = localStorage.getItem('sidebarState');
    } catch (e) {
        console.warn("Dostęp do localStorage zablokowany przez przeglądarkę.");
    }

    if (savedState === 'open') {
        sidebar.classList.remove('collapsed');
    } else if (savedState === 'closed') {
        sidebar.classList.add('collapsed');
    }

    if (hamburgerBtn && sidebar) {
        hamburgerBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            try {
                localStorage.setItem('sidebarState', sidebar.classList.contains('collapsed') ? 'closed' : 'open');
            } catch (e) {
                // Nic nie robimy, po prostu nie zapisze stanu
            }
        });
    }
}

export function initBulkSelection() {
    window.toggleSelectionMode = function(cardId) {
        const form = document.getElementById('form');
        if (form) form.classList.add('selection-mode');
        
        if (cardId) {
            const cb = document.getElementById('cb-' + cardId);
            if (cb) cb.checked = true;
        }
        
        updateBulkActionBar();
    };

    window.exitSelectionMode = function() {
        const form = document.getElementById('form');
        if (form) form.classList.remove('selection-mode');
        
        // Odznacz wszystko przy wyjściu z trybu
        document.querySelectorAll('.card-select-cb').forEach(cb => cb.checked = false);
        updateBulkActionBar();
    };

    // Nasłuchiwanie zmian na checkboxach w celu aktualizacji licznika
    document.body.addEventListener('change', function(e) {
        if (e.target.classList.contains('card-select-cb')) {
            updateBulkActionBar();
        }
    });

    function updateBulkActionBar() {
        const form = document.getElementById('form');
        const bar = document.getElementById('bulk-action-bar');
        if (!bar || !form) return;

        if (form.classList.contains('selection-mode')) {
            bar.classList.remove('d-none');
            bar.classList.add('d-flex');
            
            const count = document.querySelectorAll('.card-select-cb:checked').length;
            const countEl = document.getElementById('selected-count');
            if (countEl) countEl.textContent = count;
        } else {
            bar.classList.remove('d-flex');
            bar.classList.add('d-none');
        }
    }
}