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