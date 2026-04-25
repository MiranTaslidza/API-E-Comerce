from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 1. Testiranje prikaza svih proizvoda
def test_read_all_products():
    response = client.get("/products/")
    assert response.status_code == 200

# 2. Testiranje kada proizvod NE POSTOJI
def test_read_product_not_found():
    response = client.get("/products/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Proizvod nije pronađen"

# 3. Testiranje slanja POGREŠNIH podataka (Validation Error)
def test_create_footwear_invalid_data():
    payload = {"name": "Samo Ime Bez Cijene"}
    response = client.post("/products/footwear", json=payload)
    assert response.status_code == 422

# 4. TEST: KREIRANJE I BRISANJE (Životni ciklus)
def test_create_and_delete_footwear():
    payload = {
        "name": "Testne Patike Brisanje",
        "description": "Opis",
        "price": 10.0,
        "image_url": "http://test.com",
        "footwear_type": "patike",
        "size": 42,
        "gender": "M"
    }
    # Kreiraj
    res = client.post("/products/footwear", json=payload)
    assert res.status_code == 201
    p_id = res.json()["id"]
    
    # Obriši odmah
    assert client.delete(f"/products/{p_id}").status_code == 200
    
    # Provjeri da ga nema
    assert client.get(f"/products/{p_id}").status_code == 404

# 5. TEST: UPDATE (Ažuriranje cijene)
def test_update_footwear():
    # Napravi proizvod
    payload = {
        "name": "Patike Za Update",
        "description": "Opis",
        "price": 50.0,
        "image_url": "http://test.com",
        "footwear_type": "patike",
        "size": 40,
        "gender": "M"
    }
    create_res = client.post("/products/footwear", json=payload)
    p_id = create_res.json()["id"]

    # Pripremi nove podatke (promjena cijene)
    update_payload = payload.copy()
    update_payload["price"] = 199.99

    # Pošalji izmjenu
    update_res = client.put(f"/products/footwear/{p_id}", json=update_payload)
    assert update_res.status_code == 200
    
    # Provjeri cijenu u odgovoru
    assert update_res.json()["price"] == 199.99
    
    # Obriši na kraju da ne ostane smeće
    client.delete(f"/products/{p_id}")