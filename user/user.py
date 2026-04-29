from fastapi import APIRouter, Depends, status, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Annotated
from database import SessionLocal
from . import models
import bcrypt


router = APIRouter(
    prefix='/users',
    tags=['users']
)


def get_db():
    db = SessionLocal() # otvaranje seseije
    try:
        yield db # privremeno proslijđivanje sesije
    finally:
        db.close() # zatvaranje sesije nakon korištenja


# Pydantic model za kreiranje korisnika
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str | None = None
    address: str | None = None
    date_of_birth: str | None = None


# funkcija za hasiranje passworda (u stvarnom svijetu, koristili bismo sigurniji algoritam poput bcrypt)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')




db_dependency = Annotated[Session, Depends(get_db)] # dohvatanje podataka koje prosliđuje get_db funkcija

# funkcija za prikaz svih korisnika
@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_users(db: db_dependency):
    users = db.query(models.User).all() # dohvaćanje svih korisnika iz baze
    return users # vraćanje korisnika


# dodavanje novog korisnika
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user: UserCreate):
    # provjera da li korisnik sa istim username-om ili email-om već postoji
    existing_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")
    
    # kreiranje novog korisnika
    new_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password), # u stvarnom svijetu, ovdje bi trebali hashirati lozinku
        full_name=user.full_name,
        address=user.address,
        date_of_birth=user.date_of_birth,
        # role će se automatski postaviti na default (BUYER)
        role=models.UserRole.BUYER,
        is_verified=False,
        is_active=True
    )
    
    db.add(new_user) # dodavanje novog korisnika u sesiju
    db.commit() # spremanje promjena u bazu
    db.refresh(new_user) # osvježavanje objekta da dobije ID iz baze
    
    return new_user # vraćanje novog korisnika
    