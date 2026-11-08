from fastapi import FastAPI, HTTPException, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import os
import psycopg2
from psycopg2.extras import RealDictConnection
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field
from datetime import date

app = FastAPI()

#obsluga bledu 400
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Błąd walidacji danych wejściowych",
            "errors": exc.errors()
        }
    )

#Test: curl.exe -i -X POST http://localhost:8000/certificates -H "Content-Type: application/json" -d "{\"domain\": \"a\", \"valid_until\": \"2026-12-31\", \"status\": \"nieznany\"}"


class CertificateCreate(BaseModel):
    domain: str = Field(min_length=3, max_length=255,
                        examples=["mojadomena.pl"])
    valid_until: date = Field(examples=["2026-12-31"])
    status: str = Field(
        pattern="^(valid|warning|expired)$", examples=["valid"])


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://certuser:certpass123@db:5432/certificates"
)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


@app.on_event("startup")
def init_db():
    # tworzenie tabeli jesli nie istieje
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS certificates (
                    id SERIAL PRIMARY KEY,
                    domain VARCHAR(255) NOT NULL,
                    valid_until DATE NOT NULL,
                    status VARCHAR(50) NOT NULL
                );
            """)
            # wstawianie danych jesli tabela jest pusta
            cur.execute("SELECT COUNT(*) FROM certificates;")
            if cur.fetchone()["count"] == 0:
                cur.execute("""
                    INSERT INTO certificates (domain, valid_until, status) VALUES
                    ('example.com', '2026-12-31', 'valid'),
                    ('test.local', '2026-11-15', 'warning'),
                    ('expired.org', '2025-01-01', 'expired');
                """)
            conn.commit()

# pobieranie listy


@app.get("/certificates")
def get_certificates():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, domain, valid_until, status FROM certificates;")
            return cur.fetchall()
#Test: curl.exe -i http://localhost:8000/certificates


# pobieranie pojedynczego rekordu

@app.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, domain, valid_until, status FROM certificates WHERE id = %s;", [certificate_id])

            cert = cur.fetchone()

            if cert is None:
                raise HTTPException(
                    status_code=404, detail="Certyfikat o podanym ID nie istnieje")
            return cert
#Test: curl.exe -i http://localhost:8000/certificates/1
#Test: curl.exe -i http://localhost:8000/certificates/999


# dodawanie nowego rekordu

@app.post("/certificates", status_code=status.HTTP_201_CREATED)
def create_certificate(cert_data: CertificateCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO certificates (domain, valid_until, status)
                VALUES (%s, %s, %s)
                RETURNING id, domain, valid_until, status;
                """,
                [cert_data.domain, cert_data.valid_until, cert_data.status]
            )
            new_cert = cur.fetchone()
            conn.commit()
            return new_cert
#Test: curl.exe -i -X POST http://localhost:8000/certificates -H "Content-Type: application/json" -d '{\"domain\": \"nowadomena.pl\", \"valid_until\": \"2027-06-30\", \"status\": \"valid\"}'
#Test: curl.exe -i -X POST http://localhost:8000/certificates -H "Content-Type: application/json" -d '{\"domain\": \"a\", \"valid_until\": \"zla-data\", \"status\": \"nieznany\"}'

# usuwanie rekordu

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
#Test: curl.exe -i -X DELETE http://localhost:8000/certificates/1


# endpoint healthchech

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
#Test: curl.exe -i http://localhost:8000/health
