from fastapi import FastAPI
import os
import psycopg2
from psycopg2.extras import RealDictConnection
from psycopg2.extras import RealDictCursor

app = FastAPI()

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


@app.get("/certificates")
def get_certificates():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, domain, valid_until, status FROM certificates;")
            return cur.fetchall()
