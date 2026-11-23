// --- PRZEŁĄCZANIE EKRANÓW (WIDOKÓW) ---
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    if (viewName === 'issuers') {
        document.getElementById('view-issuers').classList.add('active');
        document.getElementById('navIssuers').classList.add('active');
        window.location.hash = 'issuers';
        loadIssuers();
    } else {
        document.getElementById('view-certificates').classList.add('active');
        document.getElementById('navCertificates').classList.add('active');
        window.location.hash = 'certificates';
        loadCertificates();
        loadIssuersDropdown();
    }
}

function setStatus(text, isError = false) {
    const el = document.getElementById('statusMessage');
    el.textContent = text;
    el.style.color = isError ? '#f87171' : '#4ade80';
}

// --- POBIERANIE CERTYFIKATÓW (API) ---
function loadCertificates() {
    fetch('/api/certificates')
        .then(res => {
            if (!res.ok) throw new Error('Błąd HTTP ' + res.status);
            return res.json();
        })
        .then(data => {
            setStatus('Pomyślnie pobrano ' + data.length + ' certyfikat(ów) z backendu (JSON)');
            const tbody = document.getElementById('certList');
            tbody.innerHTML = '';

            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#94a3b8;">Brak certyfikatów w bazie.</td></tr>';
                return;
            }

            data.forEach(item => {
                const tr = document.createElement('tr');
                let badgeClass = 'badge-valid';
                let statusText = `Ważny`;

                if (item.status === 'warning') {
                    badgeClass = 'badge-warning';
                    statusText = 'Wkrótce wygasa';
                } else if (item.status === 'expired') {
                    badgeClass = 'badge-expired';
                    const daysAgo = Math.abs(item.days_left);
                    statusText = `Wygasł`;
                }

                tr.innerHTML = `
                    <td>${item.id}</td>
                    <td><strong>${item.domain}</strong></td>
                    <td>${item.issuer_name || '<em style="color:#64748b;">Brak</em>'}</td>
                    <td>${item.valid_until}</td>
                    <td><span class="badge ${badgeClass}">${statusText}</span></td>
                    <td>
                        <button class="btn-delete" onclick="handleDeleteCertificate(${item.id})">Usuń</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => setStatus('Błąd pobierania certyfikatów: ' + err.message, true));
}

// --- POBIERANIE WYSTAWCÓW (API) ---
function loadIssuers() {
    fetch('/api/issuers')
        .then(res => {
            if (!res.ok) throw new Error('Błąd HTTP ' + res.status);
            return res.json();
        })
        .then(data => {
            setStatus('Pomyślnie pobrano ' + data.length + ' wystawców z backendu (JSON)');
            const tbody = document.getElementById('issuerList');
            tbody.innerHTML = '';

            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:#94a3b8;">Brak zarejestrowanych wystawców.</td></tr>';
                return;
            }

            data.forEach(item => {
                const tr = document.createElement('tr');
                const websiteLink = item.website ? `<a class="external-link" href="${item.website}" target="_blank">${item.website}</a>` : '<em style="color:#64748b;">Brak</em>';
                tr.innerHTML = `
                    <td>${item.id}</td>
                    <td><strong>${item.name}</strong></td>
                    <td>${websiteLink}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => setStatus('Błąd pobierania wystawców: ' + err.message, true));
}

// --- POBIERANIE WYSTAWCÓW DO SELECT W FORMULARZU ---
function loadIssuersDropdown() {
    fetch('/api/issuers')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('certIssuer');
            select.innerHTML = '<option value="">-- Brak / Nieznany --</option>';
            data.forEach(iss => {
                const opt = document.createElement('option');
                opt.value = iss.id;
                opt.textContent = `${iss.name}`;
                select.appendChild(opt);
            });
        })
        .catch(() => { });
}

// --- DODAWANIE CERTYFIKATU (POST /api/certificates) ---
function handleAddCertificate(event) {
    event.preventDefault();
    const domain = document.getElementById('certDomain').value.trim();
    const issuerIdVal = document.getElementById('certIssuer').value;
    const validUntil = document.getElementById('certValidUntil').value;

    // Ważność (status) jest wyliczana automatycznie w backendzie na podstawie daty!
    const payload = {
        domain: domain,
        valid_until: validUntil,
        issuer_id: issuerIdVal ? parseInt(issuerIdVal, 10) : null
    };

    fetch('/api/certificates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Błąd zapisu certyfikatu');
            }
            return data;
        })
        .then(() => {
            setStatus('Pomyślnie dodano nowy certyfikat (ważność wyliczona automatycznie)!');
            document.getElementById('addCertForm').reset();
            loadCertificates();
        })
        .catch(err => setStatus('Błąd: ' + err.message, true));
}

// --- USUWANIE CERTYFIKATU (DELETE /api/certificates/{id}) ---
function handleDeleteCertificate(id) {
    if (!confirm(`Czy na pewno chcesz usunąć certyfikat o ID ${id}?`)) {
        return;
    }

    fetch(`/api/certificates/${id}`, {
        method: 'DELETE'
    })
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Błąd usuwania');
            }
            return data;
        })
        .then(data => {
            setStatus(data.message);
            loadCertificates();
        })
        .catch(err => setStatus('Błąd usuwania: ' + err.message, true));
}

// --- DODAWANIE WYSTAWCY (POST /api/issuers) ---
function handleAddIssuer(event) {
    event.preventDefault();
    const name = document.getElementById('issuerName').value.trim();
    const website = document.getElementById('issuerWebsite').value.trim();

    const payload = {
        name: name,
        website: website || null
    };

    fetch('/api/issuers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Błąd zapisu wystawcy');
            }
            return data;
        })
        .then(() => {
            setStatus('Pomyślnie dodano nowego wystawcę!');
            document.getElementById('addIssuerForm').reset();
            loadIssuers();
        })
        .catch(err => setStatus('Błąd: ' + err.message, true));
}

// Inicjalizacja widoku na podstawie adresu hash
window.addEventListener('DOMContentLoaded', () => {
    if (window.location.hash === '#issuers') {
        switchView('issuers');
    } else {
        switchView('certificates');
    }
});

