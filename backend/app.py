from fastapi import FastAPI

app = FastAPI()

przykladowa_lista = [
    {"id": 1, "domain": "Adam_Malysz.pl",
        "valid_until": "2026-12-01", "status": "valid"},
    {"id": 2, "domain": "Robert_Maklowicz.com",
        "valid_until": "2026-10-15", "status": "warning"}
]


@app.get("/certificates")
async def get_certificates():
    return przykladowa_lista
