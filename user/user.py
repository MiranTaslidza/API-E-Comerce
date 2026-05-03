from fastapi import APIRouter, Depends, status, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Annotated
from database import SessionLocal
from . import models
import bcrypt
from jose import jwt
from datetime import datetime, timedelta, timezone

import base64 # za kodiranje email poruka
from email.mime.text import MIMEText # za kreiranje email poruka
from gmail_service import get_gmail_service # uvozimo tvoju skriptu



#upisati neki slučajno generisani ključ
SECRET_KEY = "DfDtSmX4lrTV2v2B6jPjDAqBVTSdjiapNKMtc3nRSLOp543qc78n9sXy2u"
ALGORITHM = "HS256"
#jedan dan ima 1440 minuta, što je 24 sata
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# funkcija za verifikacijski token emaila
def create_verification_token(email: str):
    # Koristimo timezone-aware UTC vrijeme
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# funkcija za slanje emaila sa verifikacijskim linkom
def send_verification_email(email: str, token: str):
    service = get_gmail_service()
    
    # Link koji korisnik treba da klikne
    verification_link = f"http://localhost:8000/users/verify/{token}"
    
    # Sadržaj maila
    message_text = f"Kliknite na link da potvrdite profil: {verification_link}"
    message = MIMEText(message_text)
    message['to'] = email
    message['subject'] = "Verifikacija profila - Moja Prodavnica"
    
    # Gmail API zahtijeva da poruka bude base64 enkriptovana
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    try:
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        print(f"Mail poslat na: {email}")
    except Exception as e:
        print(f"Greška pri slanju: {e}")


#router za korisnike
router = APIRouter(
    prefix='/users',
    tags=['users']
)

# funkcija za dohvatanje baze podataka (koristi se kao dependency u FastAPI-ju)
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


    # Generišemo token za ovog korisnika
    token = create_verification_token(new_user.email)
    # Šaljemo mail (ovo će aktivirati Google prozor prvi put)
    send_verification_email(new_user.email, token)
    
    return new_user # vraćanje novog korisnika

    
# funkcija za verifikaciju korisnika putem tokena
@router.get("/verify/{token}")
async def verify_user(token: str, db: db_dependency):
    try:
        # 1. Dekodiramo token da vidimo kome pripada
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
            
        # 2. Pronalazimo korisnika u bazi
        user = db.query(models.User).filter(models.User.email == email).first()
        
        # KLJUČNI DIO: Postavljamo is_verified na True
        user.is_verified = True
        db.commit() # Spasimo promjenu u bazu podataka
        return {"message": "Uspješno ste verifikovali svoj profil!"}
        
    except Exception:
        raise HTTPException(status_code=400, detail="Token has expired or is invalid")
    


