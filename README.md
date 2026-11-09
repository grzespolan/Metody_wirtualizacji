# Pilnowanie wygasających certyfikatów TLS

## Format wymiany danych (JSON)

Wymiana danych pomiędzy frontendem a backendem odbywa się wyłącznie za pośrednictwem protokołu HTTP w formacie `application/json`.

### 1. Pobieranie danych (Response JSON)

#### Lista certyfikatów (`GET /certificates`)
Odpowiedź zwraca tablicę obiektów JSON:
```json
[
  {
    "id": 1,
    "domain": "example.com",
    "valid_until": "2026-12-31",
    "status": "valid"
  },
  {
    "id": 2,
    "domain": "test.local",
    "valid_until": "2026-11-15",
    "status": "warning"
  }
]
```

#### Pojedynczy certyfikat (`GET /certificates/{id}`)
```json
{
  "id": 1,
  "domain": "example.com",
  "valid_until": "2026-12-31",
  "status": "valid"
}
```

**Opis pól struktury:**
* `id` (*integer*) – unikalny identyfikator wpisu w bazie danych.
* `domain` (*string*) – nazwa monitorowanej domeny (min. 3, max. 255 znaków).
* `valid_until` (*string / date*) – data wygaśnięcia certyfikatu w formacie ISO `YYYY-MM-DD`.
* `status` (*string*) – stan ważności certyfikatu. Dozwolone wartości zdefiniowane wyrażeniem regularnym:
  * `"valid"` – certyfikat aktywny i ważny,
  * `"warning"` – certyfikat zbliża się do terminu wygaśnięcia,
  * `"expired"` – certyfikat wygasł.

---

### 2. Przesyłanie danych (Request JSON)

#### Dodawanie nowego certyfikatu (`POST /certificates`)
Klient przesyła payload JSON bez pola `id` (generowane automatycznie przez bazę danych):
```json
{
  "domain": "twojadomena.pl",
  "valid_until": "2027-06-30",
  "status": "valid"
}
```

**Odpowiedź sukcesu (`201 Created`):**
Zwraca utworzony obiekt z przypisanym nowym ID:
```json
{
  "id": 4,
  "domain": "twojadomena.pl",
  "valid_until": "2027-06-30",
  "status": "valid"
}
```

---

### 3. Komunikaty operacyjne i status

#### Usunięcie certyfikatu (`DELETE /certificates/{id}`)
Odpowiedź sukcesu (`200 OK`):
```json
{
  "message": "Certyfikat o ID 1 został pomyślnie usunięty"
}
```

#### Sprawdzenie stanu usługi (`GET /health`)
Odpowiedź sukcesu (`200 OK`):
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

### 4. Formaty błędów (Error JSON)

#### Błąd walidacji wejściowej (`400 Bad Request`)
Zwracany, gdy przesłane dane nie spełniają reguł walidacji Pydantic (np. za krótka domena, nieprawidłowy format daty lub nieobsługiwany status):
```json
{
  "detail": "Błąd walidacji danych wejściowych",
  "errors": [
    {
      "type": "string_too_short",
      "loc": ["body", "domain"],
      "msg": "String should have at least 3 characters",
      "input": "a",
      "ctx": {
        "min_length": 3
      }
    }
  ]
}
```

#### Błąd braku rekordu (`404 Not Found`)
Zwracany, gdy certyfikat o żądanym ID nie istnieje w bazie:
```json
{
  "detail": "Certyfikat o podanym ID nie istnieje"
}
```

#### Błąd bazy danych (`503 Service Unavailable`)
```json
{
  "detail": "Database connection failed: ..."
}
```

---

# pomoc ai w zrozumieniu biblioteki fastapi oraz utworzeniu środowiska venv

# pomoc ai w napisaniu skryptu w js oraz zbudowania podstawy wizualnej strony w css

# pomoc ai w polaczeniu backendu z baza (psycopg2.extras)

#pomoc ai w generowaniu handlera walidacji
