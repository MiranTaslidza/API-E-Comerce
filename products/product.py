from fastapi import APIRouter, Depends, status, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Annotated
from database import SessionLocal
from . import models

router = APIRouter(
    prefix='/products',
    tags=['products']
)

def get_db():
    db = SessionLocal() # otvaranje seseije
    try:
        yield db # privremeno proslijđivanje sesije
    finally:
        db.close() # zatvaranje sesije nakon korištenja 

db_dependency = Annotated[Session, Depends(get_db)] # dohvatanje podataka koje prosliđuje get_db funkcija


# Pydantic modeli za validaciju podataka koje korisnik šalje prilikom kreiranja proizvoda. Ovi modeli su neophodni da bismo osigurali da su svi potrebni podaci prisutni i da su u ispravnom formatu prije nego što ih pošaljemo u bazu podataka.
class ProductRequest(BaseModel):
    name: str
    description: str
    price: float
    image_url: str

# Za Obuću 👟
class FootwearRequest(ProductRequest):
    footwear_type: str  # Tene, Čizme...
    size: int           # 42, 44...
    gender: str         # Muška, Ženska...

# Za Odjeću 👕
class ClothingRequest(ProductRequest):
    clothing_type: str
    size: str           # S, M, L...
    gender: str
    material: str

# Za Bijelu tehniku 🏠
class HomeApplianceRequest(ProductRequest):
    appliance_type: str
    brand: str
    energy_rating: str



# funkcija za prikaz svih proizvoda
@router.get('/', status_code=status.HTTP_200_OK)
async def read_all(db: db_dependency):
    return db.query(models.Product).all()


# funkcija za dodavanje proizvoda
# obuča
@router.post("/footwear", status_code=status.HTTP_201_CREATED)
async def create_footwear(db: db_dependency, request: FootwearRequest):
    # Kreiramo objekat Footwear
    # SQLAlchemy će sam vidjeti da je to Footwear i upisati "footwear" u bazu
    new_item = models.Footwear(
        name=request.name,
        description=request.description,
        price=request.price,
        image_url=request.image_url,
        footwear_type=request.footwear_type,
        size=request.size,
        gender=request.gender
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

# odjeća
@router.post("/clothing", status_code=status.HTTP_201_CREATED)
async def create_clothing(db: db_dependency, request: ClothingRequest):
    new_item = models.Clothing(
        name=request.name,
        description=request.description,
        price=request.price,
        image_url=request.image_url,
        clothing_type=request.clothing_type,
        size=request.size,
        gender=request.gender,
        material=request.material
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

# bijela tehnika
@router.post("/home_appliance", status_code=status.HTTP_201_CREATED)
async def create_home_appliance(db: db_dependency, request: HomeApplianceRequest):  
    new_item = models.HomeAppliance(
        name=request.name,
        description=request.description,
        price=request.price,
        image_url=request.image_url,
        appliance_type=request.appliance_type,
        brand=request.brand,
        energy_rating=request.energy_rating
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


