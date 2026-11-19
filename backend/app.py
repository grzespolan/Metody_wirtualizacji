from fastapi import FastAPI, HTTPException, status, Request
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
    status: str = Field(pattern="^(valid|warning|expired)$", examples=["valid"])
    issuer_id: int | None = Field(default=None, examples=[1])


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://certuser:certpass123@db:5432/certificates"
)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


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
                    ('example.com', '2026-12-31', 'valid', 1),
                    ('test.local', '2026-11-15', 'warning', 2),
                    ('expired.org', '2025-01-01', 'expired', 3);
                """)

            conn.commit()


# --- Endpointy dla wystawców (issuers) ---

@app.get("/issuers")
def get_issuers():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, website FROM issuers ORDER BY id;")
            return cur.fetchall()
# Test: curl.exe -i http://localhost:8000/issuers


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
# Test: curl.exe -i -X POST http://localhost:8000/issuers -H "Content-Type: application/json" -d '{\"name\": \"Cloudflare CA\", \"website\": \"https://cloudflare.com\"}'


# --- Endpointy dla certyfikatów (certificates) ---

@app.get("/certificates")
def get_certificates():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.domain, c.valid_until, c.status, c.issuer_id, i.name AS issuer_name
                FROM certificates c
                LEFT JOIN issuers i ON c.issuer_id = i.id
                ORDER BY c.id;
            """)
            return cur.fetchall()
# Test: curl.exe -i http://localhost:8000/certificates


@app.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.domain, c.valid_until, c.status, c.issuer_id, i.name AS issuer_name
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
# Test: curl.exe -i http://localhost:8000/certificates/1


@app.post("/certificates", status_code=status.HTTP_201_CREATED)
def create_certificate(cert_data: CertificateCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO certificates (domain, valid_until, status, issuer_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, domain, valid_until, status, issuer_id;
                    """,
                    [cert_data.domain, cert_data.valid_until, cert_data.status, cert_data.issuer_id]
                )
                new_cert = cur.fetchone()
                conn.commit()

                # Pobranie rekordu wraz z nazwą wystawcy (JOIN)
                cur.execute("""
                    SELECT c.id, c.domain, c.valid_until, c.status, c.issuer_id, i.name AS issuer_name
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
# Test: curl.exe -i -X POST http://localhost:8000/certificates -H "Content-Type: application/json" -d '{\"domain\": \"nowadomena.pl\", \"valid_until\": \"2027-06-30\", \"status\": \"valid\", \"issuer_id\": 1}'


@app.delete("/certificates/{certificate_id}")
def delete_certificate(certificate_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM certificates WHERE id = %s RETURNING id;",
                [certificate_id]
            )
            deleted = cur.fetchone()

            if deleted is None:
                raise HTTPException(
                    status_code=404,
                    detail="Certyfikat o podanym ID nie istnieje"
                )

            conn.commit()
            return {"message": f"Certyfikat o ID {certificate_id} został pomyślnie usunięty"}
# Test: curl.exe -i -X DELETE http://localhost:8000/certificates/1


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
# Test: curl.exe -i http://localhost:8000/health
