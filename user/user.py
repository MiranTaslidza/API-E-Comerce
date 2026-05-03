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
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError



#upisati neki slučajno generisani ključ
SECRET_KEY = "DfDtSmX4lrTV2v2B6jPjDAqBVTSdjiapNKMtc3nRSLOp543qc78n9sXy2u"
ALGORITHM = "HS256"

# 1. Postavimo različita vremena isteka
VERIFICATION_TOKEN_EXPIRE_HOURS = 24
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Profesionalni standard je kraće vrijeme za login

# 2. Univerzalna funkcija za kreiranje bilo kojeg JWT tokena
def create_jwt_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    
    # Ako ne pošaljemo specifično vrijeme, koristi default od 15 minuta
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
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
    token = create_jwt_token(
    data={"sub": user.email, "purpose": "verification"}, 
    expires_delta=timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS))
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
    
# login
@router.post("/login")
async def login_user(db: db_dependency, form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. PRONALAŽENJE KORISNIKA (Email ili Username)
    # Tražimo korisnika koji ima ili taj email ILI to korisničko ime
    user = db.query(models.User).filter(
        (models.User.email == form_data.username) | 
        (models.User.username == form_data.username)
    ).first()
    
    # Ako korisnik ne postoji, šaljemo grešku
    if not user:
        raise HTTPException(status_code=404, detail="Korisnik nije pronađen")
    
    # 2. PROVJERA LOZINKE (Bcrypt objašnjenje)
    # Password koji je korisnik upravo unio (form_data.password) upoređujemo sa onim iz baze
    is_password_correct = bcrypt.checkpw(
        form_data.password.encode('utf-8'), # Pretvaramo unos u bajtove
        user.password_hash.encode('utf-8')  # Pretvaramo hash iz baze u bajtove
    )
    
    if not is_password_correct:
        raise HTTPException(status_code=401, detail="Netačna lozinka")
    
    # 3. PROVJERA VERIFIKACIJE
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Profil nije verifikovan. Provjerite email.")
    
    # 4. KREIRANJE TOKENA
    access_token = create_jwt_token(
        data={"sub": user.email, "role": user.role.value}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}





# get current user funkcija koja koristi token da dohvati informacije o trenutno prijavljenom korisniku

# 1. Definišemo šemu koja kaže FastAPI-ju gdje da traži token
# tokenUrl je putanja do tvoje login funkcije
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

# 2. Funkcija koja provjerava ko je trenutno ulogovan
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: db_dependency):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nije moguće potvrditi identitet",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Dekodiramo token koji nam je korisnik poslao
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise credentials_exception
            
    except JWTError:
        # Ako je token istekao ili je neko petljao po njemu
        raise credentials_exception
        
    # Pronalazimo korisnika u bazi na osnovu emaila iz tokena
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if user is None:
        raise credentials_exception
        
    return user




#brisanje korisnika (samo vlasnik ili admin može obrisati nalog)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(db: db_dependency, user_id: int = Path(..., gt=0), current_user: models.User = Depends(get_current_user) # 1. KO VRŠI BRISANJE?
                      ):
    # 2. PRONALAŽENJE KORISNIKA KOJEG ŽELIMO OBRISATI
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Korisnik nije pronađen")
    
    # 3. PROVJERA DOZVOLE (Logička vrata)
    # Provjeravamo: da li si to TI (vlasnik) ILI si ti ADMIN?
    is_owner = current_user.id == user_to_delete.id
    is_admin = current_user.role.value == "admin" # Pretpostavljamo da ti je rola string ili Enum
    
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Nemate dozvolu za brisanje ovog naloga"
        )
    
    # 4. IZVRŠAVANJE
    db.delete(user_to_delete)
    db.commit()
    # Kod 204 ne vraća body, pa return nije obavezan, ali može stajati