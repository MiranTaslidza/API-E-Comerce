from fastapi import APIRouter, Depends, status, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Annotated
from database import SessionLocal
from . import models
from products import models as product_models
import time as python_time

# uvz get_current_user iz  user.py jer ćemo ga koristiti za provjeru da li je korisnik admin
from user.user import get_current_user
from user.models import User  # Uvozimo User klasu direktno

# Kreiranje routera za wishlist
router = APIRouter(
    prefix='/wishlist',
    tags=['wishlist']
)

# Funkcija za dobijanje DB sesije
def get_db():
    db = SessionLocal() # otvaranje seseije
    try:
        yield db # privremeno proslijđivanje sesije
    finally:
        db.close() # zatvaranje sesije nakon korištenja 

db_dependency = Annotated[Session, Depends(get_db)] # dohvatanje podataka koje prosliđuje get_db funkcija



#prikaz svih želja logovanog korisnika
@router.get("/", status_code=status.HTTP_200_OK)
async def get_wishlist(db: db_dependency, current_user: User = Depends(get_current_user)):
    # Moraš dodati .all() na kraju da bi SQLAlchemy stvarno dohvatio listu iz baze
    wishlist_items = db.query(models.Wishlist).filter(models.Wishlist.user_id == current_user.id).all()
    
    # Ako želiš da vratiš listu, vrati je direktno
    return wishlist_items



# dodavanje proizvoda
@router.post('/add/{product_id}', status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(db: db_dependency, product_id: int = Path(..., description="ID proizvoda"), current_user: User = Depends(get_current_user)):
    # 1. Provjera da li proizvod postoji
    product = db.query(product_models.Product).filter(product_models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proizvod nije pronađen")

    # 2. Provjera da li je već u wishlisti
    existing_wishlist_item = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id, 
        models.Wishlist.product_id == product_id
    ).first()
    
    if existing_wishlist_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proizvod je već u wishlisti")

    # 3. Dodavanje - koristimo int(time.time()) jer ti je u modelu Integer
    new_wishlist_item = models.Wishlist(
        user_id=current_user.id, 
        product_id=product_id,
        created_at=int(python_time.time()) # Sada koristimo sigurno ime
    )
    
    db.add(new_wishlist_item)
    db.commit()
    db.refresh(new_wishlist_item)

    return {"message": "Proizvod je dodan u wishlistu", "wishlist_item": new_wishlist_item}


# uklanjanje proizvoda iz wishlist samo korisnik uklanja svoje proizvode i izvršiti provjeru da li je več dodat postoječi proizvod u wishlisti
@router.delete('/remove/{product_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    db: db_dependency, 
    product_id: int = Path(..., description="ID proizvoda koji se uklanja"),
    current_user: User = Depends(get_current_user)
):
    # 1. Pronađi stavku u bazi
    wishlist_item = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id,
        models.Wishlist.product_id == product_id
    ).first()

    # 2. Ako ne postoji, baci grešku
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Proizvod nije u vašoj wishlisti")

    # 3. Obriši i potvrdi
    db.delete(wishlist_item)
    db.commit()
    
    return None # 204 status ne vraća tijelo odgovora