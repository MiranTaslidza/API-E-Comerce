const loginLink = document.getElementById('login-nav-link');

if (loginLink) {
    loginLink.addEventListener('click', function(event) {
        event.preventDefault(); // Zaustavlja skakanje stranice
        
        // 1. Stvaramo novi prazan 'div' element u memoriji
        const overlay = document.createElement('div');
        
        // 2. Dajemo mu CSS stilove direktno kroz JS da prekrije ekran i zamuti pozadinu
        overlay.style.position = 'fixed'; // Fiksna pozicija da ostane na mjestu čak i kad se skrola
        overlay.style.top = '0'; // Početak od vrha
        overlay.style.left = '0'; // Početak od lijeve strane
        overlay.style.width = '100%';  // Širina preko cijelog ekrana
        overlay.style.height = '100%'; // Visina preko cijelog ekrana
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)'; // Tamna prozirna pozadina
        overlay.style.backdropFilter = 'blur(2px)';         // Ovo radi zamućenje (blur)
        overlay.style.zIndex = '9999';
        
        //pomicanje  prozor diva u sredinu ekrana
        overlay.style.display = 'flex';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        
        // 1. Stvaramo novi prazan 'div' koji će biti naš prozor
        const prozor = document.createElement('div');

        // 2. Dajemo mu stilove prema onoj tvojoj zelenoj cyberpunk slici
        prozor.style.width = '360px'; // Fiksna širina prozora
        prozor.style.minHeight = '400px'; // Minimalna visina prozora
        prozor.style.backgroundColor = '#050505';     // Skoro crna pozadina
        prozor.style.border = '2px solid #00ff33';     // Prepoznatljiva zelena cyber linija
        prozor.style.borderRadius = '8px';             // Blago zaobljeni kutovi
        prozor.style.boxShadow = '0 0 20px #00ff33';   // Zeleni sjaj (neon efekt)
        prozor.style.padding = '20px';              // Unutrašnji razmak

        // 3. Dodajemo HTML sadržaj unutar našeg prozora
        prozor.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #00ff33; padding-bottom: 5px; font-family: 'Courier New', Courier, monospace;">
                <span style="font-size: 22px; margin: 0px auto; color: #00ff33; letter-spacing: 1px;">Login E-Commerce</span>
                <span id="zatvori-cyber-btn" style="cursor: pointer; font-weight: bold; font-size: 20px; color: #00ff33;">&times;</span>
            </div>

            <!-- Sadržaj forme za login -->
            <form id="cyber-login-form" style="font-family: 'Courier New', Courier, monospace; color: #00ff33;">
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 14px; letter-spacing: 1px;"> ENTER EMAIL AND USERNAME:</label>
                    <input type="text" id="cyber-email" required style="width: 100%; padding: 10px; background-color: #111; border: 1px solid #00ff33; color: #00ff33; border-radius: 4px; outline: none; box-shadow: inset 0 0 5px rgba(0,255,51,0.2);">
                </div>

                <div style="margin-bottom: 30px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 14px; letter-spacing: 1px;"> ENTER PASSWORD:</label>
                    <input type="password" id="cyber-password" required style="width: 100%; padding: 10px; background-color: #111; border: 1px solid #00ff33; color: #00ff33; border-radius: 4px; outline: none; box-shadow: inset 0 0 5px rgba(0,255,51,0.2);">
                </div>

                <button type="submit" style="width: 100%; padding: 12px; background-color: transparent; border: 2px solid #00ff33; color: #00ff33; font-weight: bold; font-size: 16px; cursor: pointer; border-radius: 4px; box-shadow: 0 0 10px rgba(0,255,51,0.3); transition: all 0.3s ease;">
                    LOGIN
                </button>

            </form>
        `;
        
        // 3. Ubacujemo prozor UNUTAR overlay-a
        overlay.appendChild(prozor);

        // 3. Dodajemo ovaj kreirani overlay na dno body-a u naš HTML
        document.body.appendChild(overlay);

        // 4. Tražimo gumb za zatvaranje koji smo maloprije stvorili kroz innerHTML
        const zatvoriBtn = document.getElementById('zatvori-cyber-btn');
        if (zatvoriBtn) {
            zatvoriBtn.addEventListener('click', function() {
                // Metoda .remove() potpuno briše element i sav njegov sadržaj iz HTML-a
                overlay.remove();
            });
        }

        // 5. Hvatanje forme i slanje podataka
        const loginForm = document.getElementById('cyber-login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', function(e) {
                e.preventDefault(); // Sprječava osvježavanje stranice prilikom slanja forme

                // Kupimo unese vrijednosti iz polja
                const email = document.getElementById('cyber-email').value;
                const password = document.getElementById('cyber-password').value;

                // Privremena provjera u konzoli da vidimo radi li sve
                // console.log("Podaci spremni za backend:");
                // console.log("Email/Username:", email);
                // console.log("Password:", password);

                // Ovdje će ići naš fetch() za slanje na FastAPI...
                fetch('/users/login', { //users/login je ruta na backendu koja je napravljena za login

                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'  // Ovo govori backendu da šaljemo JSON podatke

                    },
                    body: JSON.stringify({
                        username_or_email: email, // Mapiramo tvoj email na ključ koji backend traži
                        password: password
                    })
                })
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    } else {
                        return response.json().then(err => { throw new Error(err.detail); });
                    }
                })
                .then(data => {
                    console.log("Uspješan login! Tokeni:", data);
                    // 1. Spremamo access_token u memoriju browsera
                    localStorage.setItem('access_token', data.access_token);

                    alert("Uspješan login!");
                    overlay.remove(); 
                })
                .catch(error => {
                    console.error("Greška:", error.message);
                    alert("Greška: " + error.message);
                });

                
            });
        }
    });
}
