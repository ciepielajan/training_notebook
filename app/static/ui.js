export function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const hamburgerBtn = document.getElementById('hamburger-btn');
    
    if (localStorage.getItem('sidebarState') === 'open') {
        sidebar.classList.remove('collapsed');
    } else if (localStorage.getItem('sidebarState') === 'closed') {
        sidebar.classList.add('collapsed');
    }

    if (hamburgerBtn && sidebar) {
        hamburgerBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            localStorage.setItem('sidebarState', sidebar.classList.contains('collapsed') ? 'closed' : 'open');
        });
    }
}