-- 1. Tabela wystawców
CREATE TABLE IF NOT EXISTS issuers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    website VARCHAR(255)
);

-- 2. Tabela certyfikatów
CREATE TABLE IF NOT EXISTS certificates (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    valid_until DATE NOT NULL,
    status VARCHAR(50) NOT NULL,
    issuer_id INTEGER REFERENCES issuers(id) ON DELETE SET NULL
);

-- 3. Tabela historii zmian (powiązana z zasobem certificates)
CREATE TABLE IF NOT EXISTS certificate_history (
    id SERIAL PRIMARY KEY,
    certificate_id INTEGER REFERENCES certificates(id) ON DELETE SET NULL,
    domain VARCHAR(255) NOT NULL,
    action VARCHAR(20) NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    details TEXT,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Dane startowe
INSERT INTO issuers (name, website) VALUES
    ('Let''s Encrypt', 'https://letsencrypt.org'),
    ('DigiCert', 'https://www.digicert.com'),
    ('Sectigo', 'https://sectigo.com');

INSERT INTO certificates (domain, valid_until, status, issuer_id) VALUES
    ('example.com', CURRENT_DATE + INTERVAL '180 days', 'valid', 1),
    ('test.local', CURRENT_DATE + INTERVAL '4 days', 'warning', 2),
    ('expired.org', CURRENT_DATE - INTERVAL '15 days', 'expired', 3);

INSERT INTO certificate_history (certificate_id, domain, action, changed_by, details) VALUES
    (1, 'example.com', 'CREATED', 'system', 'Inicjalizacja bazy danych'),
    (2, 'test.local', 'CREATED', 'system', 'Inicjalizacja bazy danych'),
    (3, 'expired.org', 'CREATED', 'system', 'Inicjalizacja bazy danych');
