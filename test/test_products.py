import pytest
from fastapi.testclient import TestClient
from main import app # Uvoziš svoj FastAPI app

# Pravimo klijenta koji će "glumiti" browser/Swagger
client = TestClient(app)

def test_read_all_products():
    # 1. AKCIJA: Pozovi rutu za prikaz svih proizvoda
    response = client.get("/products/") # Stavi ovdje tačnu putanju tvoje rute
    
    # 2. PROVJERA: Da li je status 200 (OK)?
    assert response.status_code == 200
    
    # 3. PROVJERA: Da li je odgovor lista (JSON)?
    assert isinstance(response.json(), list)


def test_create_footwear_success():
    # Podaci koje šaljemo (kao u Swaggeru)
    payload = {
        "name": "Test Tene",
        "description": "Neki opis",
        "price": 120.5,
        "image_url": "http://slika.com",
        "footwear_type": "patike",
        "size": 44,
        "gender": "M"
    }
    
    # Šaljemo POST zahtjev
    response = client.post("/products/footwear", json=payload)
    
    # Provjeravamo da li je kreirano (201)
    assert response.status_code == 201
    
    # Provjeravamo da li nam je vratio ispravno ime
    data = response.json()
    assert data["name"] == "Test Tene"
    assert "id" in data # Provjeravamo da li je baza dodijelila ID


def test_read_product_not_found():
    # Pokušavamo dohvatiti ID koji sigurno nemamo (npr. 999999)
    response = client.get("/products/999999")
    
    # Provjeravamo da li je status 404
    assert response.status_code == 404
    # Provjeravamo da li je poruka ona koju smo napisali u routeru
    assert response.json()["detail"] == "Proizvod nije pronađen"

def test_create_footwear_invalid_data():
    # Šaljemo nepotpune podatke (nema cijene, nema veličine)
    payload = {
        "name": "Loše patike"
    }
    response = client.post("/products/footwear", json=payload)
    
    # FastAPI ovo ne smije pustiti dalje od vrata
    assert response.status_code == 422