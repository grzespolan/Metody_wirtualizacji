-- Skrypt inicjalizujący schemat bazy danych i dane startowe dla PostgreSQL
-- Wykonywany automatycznie przez oficjalny obraz postgres z katalogu /docker-entrypoint-initdb.d/

-- 1. Tabela wystawców certyfikatów (Issuers / Certificate Authorities)
CREATE TABLE IF NOT EXISTS issuers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    website VARCHAR(255)
);

-- 2. Tabela certyfikatów powiązana kluczem obcym (FOREIGN KEY) z tabelą issuers
CREATE TABLE IF NOT EXISTS certificates (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    valid_until DATE NOT NULL,
    status VARCHAR(50) NOT NULL,
    issuer_id INTEGER REFERENCES issuers(id) ON DELETE SET NULL
);

-- Dane startowe dla tabeli wystawców
INSERT INTO issuers (name, website) VALUES
    ('Let''s Encrypt', 'https://letsencrypt.org'),
    ('DigiCert', 'https://www.digicert.com'),
    ('Sectigo', 'https://sectigo.com');

-- Dane startowe dla tabeli certyfikatów
INSERT INTO certificates (domain, valid_until, status, issuer_id) VALUES
    ('example.com', '2026-12-31', 'valid', 1),
    ('test.local', '2026-11-15', 'warning', 2),
    ('expired.org', '2025-01-01', 'expired', 3);

