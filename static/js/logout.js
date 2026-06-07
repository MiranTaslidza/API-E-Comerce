document.addEventListener('DOMContentLoaded', () => {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault(); // OVDJE STVARNO ZAUSTAVLJAŠ BROWSER DA NE IDE NA BACKEND
            
            // 1. Brišemo kolačić (pazi na path, mora biti isti kao kad si ga postavio)
            document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            
            // 2. Brišemo localStorage
            localStorage.removeItem('access_token');
            
            // 3. Opciono: obavijesti server da si se odjavio (ako želiš da se obriše refresh_token iz baze)
            fetch('/logout', { method: 'POST' }); 
            
            // 4. Forsirano osvježavanje na početnu
            window.location.href = "/users";
        });
    }
});