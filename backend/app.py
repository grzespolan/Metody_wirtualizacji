from fastapi import FastAPI, HTTPException, status, Request, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field
from datetime import date

app = FastAPI()


# Obsługa błędu 400 dla błędów walidacji
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Błąd walidacji danych wejściowych",
            "errors": exc.errors()
        }
    )


class IssuerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100, examples=["Let's Encrypt"])
    website: str | None = Field(default=None, max_length=255, examples=["https://letsencrypt.org"])


class CertificateCreate(BaseModel):
    domain: str = Field(min_length=3, max_length=255, examples=["mojadomena.pl"])
    valid_until: date = Field(examples=["2026-12-31"])
    status: str | None = Field(default=None, pattern="^(valid|warning|expired)$", examples=["valid"])
    issuer_id: int | None = Field(default=None, examples=[1])


class CertificateUpdate(BaseModel):
    domain: str | None = Field(default=None, min_length=3, max_length=255, examples=["nowadomena.pl"])
    valid_until: date | None = Field(default=None, examples=["2027-05-01"])
    issuer_id: int | None = Field(default=None, examples=[2])


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://certuser:certpass123@db:5432/certificates"
)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def calculate_status(valid_until: date) -> str:
    """Automatyczne wyliczanie statusu na podstawie daty wygaśnięcia."""
    days_left = (valid_until - date.today()).days
    if days_left < 0:
        return "expired"
    elif days_left < 7:
        return "warning"
    else:
        return "valid"


def log_history(cur, certificate_id: int | None, domain: str, action: str, changed_by: str, details: str | None = None):
    """Zapisuje zdarzenie w tabeli historii zmian."""
    cur.execute(
        """
        INSERT INTO certificate_history (certificate_id, domain, action, changed_by, details)
        VALUES (%s, %s, %s, %s, %s);
        """,
        [certificate_id, domain, action, changed_by, details]
    )


@app.on_event("startup")
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Tabela wystawców certyfikatów
            cur.execute("""
                CREATE TABLE IF NOT EXISTS issuers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    website VARCHAR(255)
                );
            """)

            # 2. Tabela certyfikatów powiązana kluczem obcym
            cur.execute("""
                CREATE TABLE IF NOT EXISTS certificates (
                    id SERIAL PRIMARY KEY,
                    domain VARCHAR(255) NOT NULL,
                    valid_until DATE NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    issuer_id INTEGER REFERENCES issuers(id) ON DELETE SET NULL
                );
            """)

            # W razie gdyby tabela certificates już istniała bez kolumny issuer_id
            cur.execute("""
                ALTER TABLE certificates 
                ADD COLUMN IF NOT EXISTS issuer_id INTEGER REFERENCES issuers(id) ON DELETE SET NULL;
            """)

            # 3. Tabela historii zmian powiązana z zasobem certificates
            cur.execute("""
                CREATE TABLE IF NOT EXISTS certificate_history (
                    id SERIAL PRIMARY KEY,
                    certificate_id INTEGER REFERENCES certificates(id) ON DELETE SET NULL,
                    domain VARCHAR(255) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    changed_by VARCHAR(100) NOT NULL,
                    details TEXT,
                    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Dane startowe dla issuers
            cur.execute("SELECT COUNT(*) FROM issuers;")
            if cur.fetchone()["count"] == 0:
                cur.execute("""
                    INSERT INTO issuers (name, website) VALUES
                    ('Let''s Encrypt', 'https://letsencrypt.org'),
                    ('DigiCert', 'https://www.digicert.com'),
                    ('Sectigo', 'https://sectigo.com');
                """)

            # Dane startowe dla certificates
            cur.execute("SELECT COUNT(*) FROM certificates;")
            if cur.fetchone()["count"] == 0:
                cur.execute("""
                    INSERT INTO certificates (domain, valid_until, status, issuer_id) VALUES
                    ('example.com', CURRENT_DATE + INTERVAL '180 days', 'valid', 1),
                    ('test.local', CURRENT_DATE + INTERVAL '4 days', 'warning', 2),
                    ('expired.org', CURRENT_DATE - INTERVAL '15 days', 'expired', 3);
                """)

            # Dane startowe dla certificate_history
            cur.execute("SELECT COUNT(*) FROM certificate_history;")
            if cur.fetchone()["count"] == 0:
                cur.execute("""
                    INSERT INTO certificate_history (certificate_id, domain, action, changed_by, details)
                    SELECT id, domain, 'CREATED', 'system', 'Inicjalizacja bazy danych'
                    FROM certificates;
                """)

            conn.commit()


# --- Endpointy dla wystawców (issuers) ---

@app.get("/issuers")
def get_issuers():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, website FROM issuers ORDER BY id;")
            return cur.fetchall()


@app.post("/issuers", status_code=status.HTTP_201_CREATED)
def create_issuer(issuer_data: IssuerCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO issuers (name, website)
                VALUES (%s, %s)
                RETURNING id, name, website;
                """,
                [issuer_data.name, issuer_data.website]
            )
            new_issuer = cur.fetchone()
            conn.commit()
            return new_issuer


# --- Endpointy dla certyfikatów (certificates) ---

@app.get("/certificates")
def get_certificates():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.id, 
                    c.domain, 
                    c.valid_until, 
                    CASE 
                        WHEN c.valid_until < CURRENT_DATE THEN 'expired'
                        WHEN (c.valid_until - CURRENT_DATE) < 7 THEN 'warning'
                        ELSE 'valid'
                    END AS status,
                    (c.valid_until - CURRENT_DATE) AS days_left,
                    c.issuer_id, 
                    i.name AS issuer_name
                FROM certificates c
                LEFT JOIN issuers i ON c.issuer_id = i.id
                ORDER BY c.id;
            """)
            return cur.fetchall()


@app.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.id, 
                    c.domain, 
                    c.valid_until, 
                    CASE 
                        WHEN c.valid_until < CURRENT_DATE THEN 'expired'
                        WHEN (c.valid_until - CURRENT_DATE) < 7 THEN 'warning'
                        ELSE 'valid'
                    END AS status,
                    (c.valid_until - CURRENT_DATE) AS days_left,
                    c.issuer_id, 
                    i.name AS issuer_name
                FROM certificates c
                LEFT JOIN issuers i ON c.issuer_id = i.id
                WHERE c.id = %s;
            """, [certificate_id])

            cert = cur.fetchone()
            if cert is None:
                raise HTTPException(
                    status_code=404, detail="Certyfikat o podanym ID nie istnieje"
                )
            return cert


@app.post("/certificates", status_code=status.HTTP_201_CREATED)
def create_certificate(cert_data: CertificateCreate, x_user: str = Header(default="admin", alias="X-User")):
    auto_status = cert_data.status or calculate_status(cert_data.valid_until)
    author = x_user.strip() or "admin"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO certificates (domain, valid_until, status, issuer_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, domain, valid_until, status, issuer_id;
                    """,
                    [cert_data.domain, cert_data.valid_until, auto_status, cert_data.issuer_id]
                )
                new_cert = cur.fetchone()

                # Zapis w historii zmian
                log_history(
                    cur,
                    new_cert["id"],
                    cert_data.domain,
                    "CREATED",
                    author,
                    f"Dodano certyfikat ważny do {cert_data.valid_until}"
                )

                conn.commit()

                cur.execute("""
                    SELECT 
                        c.id, 
                        c.domain, 
                        c.valid_until, 
                        CASE 
                            WHEN c.valid_until < CURRENT_DATE THEN 'expired'
                            WHEN (c.valid_until - CURRENT_DATE) < 7 THEN 'warning'
                            ELSE 'valid'
                        END AS status,
                        (c.valid_until - CURRENT_DATE) AS days_left,
                        c.issuer_id, 
                        i.name AS issuer_name
                    FROM certificates c
                    LEFT JOIN issuers i ON c.issuer_id = i.id
                    WHERE c.id = %s;
                """, [new_cert["id"]])
                return cur.fetchone()
            except psycopg2.Error as e:
                conn.rollback()
                if "violates foreign key constraint" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Wystawca o ID {cert_data.issuer_id} nie istnieje."
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Błąd bazy danych: {str(e)}"
                )


@app.put("/certificates/{certificate_id}")
def update_certificate(certificate_id: int, cert_data: CertificateUpdate, x_user: str = Header(default="admin", alias="X-User")):
    author = x_user.strip() or "admin"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, domain, valid_until, issuer_id FROM certificates WHERE id = %s;", [certificate_id])
            existing = cur.fetchone()

            if existing is None:
                raise HTTPException(
                    status_code=404,
                    detail="Certyfikat o podanym ID nie istnieje"
                )

            new_domain = cert_data.domain if cert_data.domain is not None else existing["domain"]
            new_valid_until = cert_data.valid_until if cert_data.valid_until is not None else existing["valid_until"]
            new_issuer_id = cert_data.issuer_id if "issuer_id" in cert_data.model_fields_set else existing["issuer_id"]
            new_status = calculate_status(new_valid_until)

            changes = []
            if new_domain != existing["domain"]:
                changes.append(f"domena: {existing['domain']} -> {new_domain}")
            if new_valid_until != existing["valid_until"]:
                changes.append(f"data: {existing['valid_until']} -> {new_valid_until}")
            if new_issuer_id != existing["issuer_id"]:
                changes.append(f"issuer_id: {existing['issuer_id']} -> {new_issuer_id}")

            details_text = "Zmieniono (" + ", ".join(changes) + ")" if changes else "Zaktualizowano rekord bez zmiany pól"

            try:
                cur.execute(
                    """
                    UPDATE certificates
                    SET domain = %s, valid_until = %s, status = %s, issuer_id = %s
                    WHERE id = %s;
                    """,
                    [new_domain, new_valid_until, new_status, new_issuer_id, certificate_id]
                )

                log_history(cur, certificate_id, new_domain, "UPDATED", author, details_text)
                conn.commit()

                cur.execute("""
                    SELECT 
                        c.id, 
                        c.domain, 
                        c.valid_until, 
                        CASE 
                            WHEN c.valid_until < CURRENT_DATE THEN 'expired'
                            WHEN (c.valid_until - CURRENT_DATE) < 7 THEN 'warning'
                            ELSE 'valid'
                        END AS status,
                        (c.valid_until - CURRENT_DATE) AS days_left,
                        c.issuer_id, 
                        i.name AS issuer_name
                    FROM certificates c
                    LEFT JOIN issuers i ON c.issuer_id = i.id
                    WHERE c.id = %s;
                """, [certificate_id])
                return cur.fetchone()
            except psycopg2.Error as e:
                conn.rollback()
                if "violates foreign key constraint" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Wystawca o ID {new_issuer_id} nie istnieje."
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Błąd bazy danych: {str(e)}"
                )


@app.delete("/certificates/{certificate_id}")
def delete_certificate(certificate_id: int, x_user: str = Header(default="admin", alias="X-User")):
    author = x_user.strip() or "admin"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM certificates WHERE id = %s RETURNING id, domain;",
                [certificate_id]
            )
            deleted = cur.fetchone()

            if deleted is None:
                raise HTTPException(
                    status_code=404,
                    detail="Certyfikat o podanym ID nie istnieje"
                )

            # Zapis usunięcia w tabeli historii (certificate_id = None po usunięciu zasobu)
            log_history(
                cur,
                None,
                deleted["domain"],
                "DELETED",
                author,
                f"Usunięto certyfikat ID {certificate_id} ({deleted['domain']})"
            )

            conn.commit()
            return {"message": f"Certyfikat o ID {certificate_id} został pomyślnie usunięty"}


# --- Endpoint historii zmian ---

@app.get("/history")
def get_history():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, certificate_id, domain, action, changed_by, details, changed_at
                FROM certificate_history
                ORDER BY changed_at DESC, id DESC;
            """)
            return cur.fetchall()


# --- Healthcheck ---

@app.get("/health")
def health_check():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )
