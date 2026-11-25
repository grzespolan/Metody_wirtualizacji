// Przechowywanie listy certyfikatów do edycji
let currentCertificates = [];

// --- POBIERANIE AKTYWNEGO OPERATORA (KTO WYKONUJE ZMIANĘ) ---
function getOperatorName() {
    const input = document.getElementById('operatorName');
    const name = input ? input.value.trim() : '';
    return name || 'admin';
}

// --- PRZEŁĄCZANIE EKRANÓW (WIDOKÓW) ---
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    if (viewName === 'issuers') {
        document.getElementById('view-issuers').classList.add('active');
        document.getElementById('navIssuers').classList.add('active');
        window.location.hash = 'issuers';
        loadIssuers();
    } else if (viewName === 'history') {
        document.getElementById('view-history').classList.add('active');
        document.getElementById('navHistory').classList.add('active');
        window.location.hash = 'history';
        loadHistory();
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
            currentCertificates = data;
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
                let statusText = `✅ Ważny (${item.days_left} dni)`;

                if (item.status === 'warning') {
                    badgeClass = 'badge-warning';
                    statusText = item.days_left === 0 ? '⚠️ Wkrótce wygasa (dzisiaj!)' : `⚠️ Wkrótce wygasa (za ${item.days_left} dni)`;
                } else if (item.status === 'expired') {
                    badgeClass = 'badge-expired';
                    const daysAgo = Math.abs(item.days_left);
                    statusText = `❌ Wygasł (${daysAgo} ${daysAgo === 1 ? 'dzień' : 'dni'} temu)`;
                }

                tr.innerHTML = `
                    <td>${item.id}</td>
                    <td><strong>${item.domain}</strong></td>
                    <td>${item.issuer_name || '<em style="color:#64748b;">Brak</em>'}</td>
                    <td>${item.valid_until}</td>
                    <td><span class="badge ${badgeClass}">${statusText}</span></td>
                    <td class="actions-cell">
                        <button class="btn-edit" onclick="openEditCertificate(${item.id})">Edytuj</button>
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

// --- POBIERANIE HISTORII ZMIAN (API) ---
function loadHistory() {
    fetch('/api/history')
        .then(res => {
            if (!res.ok) throw new Error('Błąd HTTP ' + res.status);
            return res.json();
        })
        .then(data => {
            setStatus('Pomyślnie pobrano ' + data.length + ' wpis(ów) z historii zmian');
            const tbody = document.getElementById('historyList');
            tbody.innerHTML = '';

            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#94a3b8;">Brak zarejestrowanych zmian w historii.</td></tr>';
                return;
            }

            data.forEach(item => {
                const tr = document.createElement('tr');
                const dateFormatted = item.changed_at ? item.changed_at.replace('T', ' ').substring(0, 19) : '-';

                let actionBadge = 'badge-valid';
                if (item.action === 'UPDATED') actionBadge = 'badge-updated';
                if (item.action === 'DELETED') actionBadge = 'badge-expired';

                tr.innerHTML = `
                    <td style="white-space: nowrap; color: #94a3b8;">${dateFormatted}</td>
                    <td><span class="badge ${actionBadge}">${item.action}</span></td>
                    <td><strong>${item.domain}</strong></td>
                    <td>${item.changed_by}</td>
                    <td style="color: #cbd5e1; font-size: 0.9rem;">${item.details || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => setStatus('Błąd pobierania historii: ' + err.message, true));
}

// --- POBIERANIE WYSTAWCÓW DO SELECT W FORMULARZACH ---
function loadIssuersDropdown() {
    fetch('/api/issuers')
        .then(res => res.json())
        .then(data => {
            const selects = [document.getElementById('certIssuer'), document.getElementById('editCertIssuer')];
            selects.forEach(select => {
                if (!select) return;
                const currentVal = select.value;
                select.innerHTML = '<option value="">-- Brak / Nieznany --</option>';
                data.forEach(iss => {
                    const opt = document.createElement('option');
                    opt.value = iss.id;
                    opt.textContent = `${iss.name}`;
                    select.appendChild(opt);
                });
                if (currentVal) select.value = currentVal;
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

    const payload = {
        domain: domain,
        valid_until: validUntil,
        issuer_id: issuerIdVal ? parseInt(issuerIdVal, 10) : null
    };

    fetch('/api/certificates', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-User': getOperatorName()
        },
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
            setStatus(`Pomyślnie dodano nowy certyfikat (operator: ${getOperatorName()})!`);
            document.getElementById('addCertForm').reset();
            loadCertificates();
        })
        .catch(err => setStatus('Błąd: ' + err.message, true));
}

// --- EDYCJA CERTYFIKATU (PUT /api/certificates/{id}) ---
function openEditCertificate(id) {
    const cert = currentCertificates.find(c => c.id === id);
    if (!cert) return;

    document.getElementById('editCertId').value = cert.id;
    document.getElementById('editCertIdLabel').textContent = cert.id;
    document.getElementById('editCertDomain').value = cert.domain;
    document.getElementById('editCertValidUntil').value = cert.valid_until;
    document.getElementById('editCertIssuer').value = cert.issuer_id || '';

    const editCard = document.getElementById('editCertCard');
    editCard.style.display = 'block';
    editCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function cancelEditCertificate() {
    document.getElementById('editCertCard').style.display = 'none';
    document.getElementById('editCertForm').reset();
}

function handleUpdateCertificate(event) {
    event.preventDefault();
    const id = document.getElementById('editCertId').value;
    const domain = document.getElementById('editCertDomain').value.trim();
    const issuerIdVal = document.getElementById('editCertIssuer').value;
    const validUntil = document.getElementById('editCertValidUntil').value;

    const payload = {
        domain: domain,
        valid_until: validUntil,
        issuer_id: issuerIdVal ? parseInt(issuerIdVal, 10) : null
    };

    fetch(`/api/certificates/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-User': getOperatorName()
        },
        body: JSON.stringify(payload)
    })
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Błąd aktualizacji certyfikatu');
            }
            return data;
        })
        .then(() => {
            setStatus(`Zaktualizowano certyfikat ID ${id} (operator: ${getOperatorName()})!`);
            cancelEditCertificate();
            loadCertificates();
        })
        .catch(err => setStatus('Błąd edycji: ' + err.message, true));
}

// --- USUWANIE CERTYFIKATU (DELETE /api/certificates/{id}) ---
function handleDeleteCertificate(id) {
    if (!confirm(`Czy na pewno chcesz usunąć certyfikat o ID ${id}?`)) {
        return;
    }

    fetch(`/api/certificates/${id}`, {
        method: 'DELETE',
        headers: {
            'X-User': getOperatorName()
        }
    })
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Błąd usuwania');
            }
            return data;
        })
        .then(data => {
            setStatus(`${data.message} (operator: ${getOperatorName()})`);
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

// Inicjalizacja widoku na podstawie adresu hash oraz zapamiętanie operatora
window.addEventListener('DOMContentLoaded', () => {
    const operatorInput = document.getElementById('operatorName');
    const savedOp = localStorage.getItem('tls_operator_name');
    if (savedOp && operatorInput) {
        operatorInput.value = savedOp;
    }
    if (operatorInput) {
        operatorInput.addEventListener('input', () => {
            localStorage.setItem('tls_operator_name', operatorInput.value.trim() || 'admin');
        });
    }

    if (window.location.hash === '#issuers') {
        switchView('issuers');
    } else if (window.location.hash === '#history') {
        switchView('history');
    } else {
        switchView('certificates');
    }
});
