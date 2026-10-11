from fastapi import FastAPI
import json

app = FastAPI()


@app.get("/certificates")
async def get_certificates():
    with open("db.json", "r", encoding="utf-8") as file:
        data = json.load(file)
        return data
