export function initImportExport() {
    const importBtn = document.getElementById('sidebar-import-btn');
    const fileInput = document.getElementById('sidebar-file-input');
    const submitBtn = document.getElementById('sidebar-submit-btn');

    if (importBtn && fileInput && submitBtn) {
        importBtn.addEventListener('click', (e) => {
            e.preventDefault();
            fileInput.click();
        });

        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                submitBtn.click();
            }
        });
    }
}