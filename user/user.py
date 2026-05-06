import uuid

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
import os
from dotenv import load_dotenv

# Ova linija "aktivira" tvoj .env fajl
load_dotenv()

###########################################################################################
# --- UVOZ PODATAKA IZ .env ---
# Za tekstualne vrijednosti (stringove)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
# Za brojeve (moramo ih pretvoriti u int jer .env sve čita kao tekst)
VERIFICATION_TOKEN_EXPIRE_HOURS = int(os.getenv("VERIFICATION_TOKEN_EXPIRE_HOURS", 24))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
# Uzimamo mail iz ENV i odmah skidamo nevidljive razmake i pretvaramo u mala slova
admin_from_env = os.getenv("ADMIN_EMAILS", "").strip().lower()
# Osnovna adresa za linkove u mailovima
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000") # 
#########################################################################################


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
    verification_link = f"{BASE_URL}/users/verify/{token}"
    
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


######################################################
#######################routeri########################
# funkcija za prikaz svih korisnika 
# izmjena da  samo admin ima pristup ovoj ruti
@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_users(db: db_dependency, current_user: models.User = Depends(get_current_user)):
    # Provjera da li je korisnik admin
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Samo admin može vidjeti sve korisnike")
    
    users = db.query(models.User).all() # dohvaćanje svih korisnika iz baze
    return users # vraćanje korisnika

# funkcija za prikaz jednog korisnika po ID-u vidi korisnik i admin
@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_by_id(user_id: int, db: db_dependency, current_user: models.User = Depends(get_current_user)):
    # Provjera da li je korisnik i admin ili vlasnik profila
    if current_user.role != models.UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nemate dozvolu za pristup ovom profilu")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Korisnik nije pronađen")
    return user

# krieranje novog korisnika
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user: UserCreate):

    # provjera da li korisnik sa istim username-om ili email-om već postoji
    existing_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")
    
    # --- NOVO: LOGIKA ZA ADMIN PROVJERU ---
    # 1. Dohvatamo string iz .env fajla i odmah ga čistimo (.strip() uklanja razmake, .lower() smanjuje slova)
    # --- NOVO: LOGIKA ZA ADMIN PROVJERU ---
    admin_email_env = os.getenv("ADMIN_EMAILS", "").strip().lower()
    user_email_to_check = user.email.strip().lower()

    # Dodajemo ovaj print da u terminalu VRLO JASNO vidiš poređenje
    print(f"POREĐENJE: '{user_email_to_check}' == '{admin_email_env}'")

    if user_email_to_check == admin_email_env:
        print("MATCH PRONAĐEN!")
        initial_role = models.UserRole.ADMIN
    else:
        print("NEMA MATCH-A!")
        initial_role = models.UserRole.BUYER
    # --------------------------------------
    
    # kreiranje novog korisnika
    new_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password), # u stvarnom svijetu, ovdje bi trebali hashirati lozinku
        full_name=user.full_name,
        address=user.address,
        date_of_birth=user.date_of_birth,
        # Ovdje koristimo našu novu varijablu 'initial_role' umjesto fiksnog BUYER
        role=initial_role,
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


# UPDATE KORISNIKA (samo vlasnik)
@router.put("/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(db: db_dependency, user_id: int = Path(..., gt=0), user_update: UserCreate = None, current_user: models.User = Depends(get_current_user)):
    # 1. PRONALAŽENJE KORISNIKA KOJEG ŽELIMO AŽURIRATI
    user_to_update = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user_to_update:
        raise HTTPException(status_code=404, detail="Korisnik nije pronađen")
    
    # 2. PROVJERA DOZVOLE (Samo vlasnik može ažurirati svoj profil)
    if current_user.id != user_to_update.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Nemate dozvolu za ažuriranje ovog naloga"
        )
    
    # 3. AŽURIRANJE POLJA (ako su poslana)
    if user_update.username:
        user_to_update.username = user_update.username
    if user_update.full_name is not None: # Dozvoljavamo i brisanje imena ako se pošalje null
        user_to_update.full_name = user_update.full_name
    if user_update.address is not None:
        user_to_update.address = user_update.address
    if user_update.date_of_birth is not None:
        user_to_update.date_of_birth = user_update.date_of_birth
    
    db.commit() # Spasimo promjene u bazu
    db.refresh(user_to_update) # Osvježimo objekat da dobijemo najnovije podatke
    
    return user_to_update


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


#update maila (samo vlasnik)
#################################
# 1. Funkcija koja koristi tvoj Gmail API za slanje linkova
def posalji_mail_za_promjenu(email: str, token: str, tip: str):
    service = get_gmail_service()
    
    # Koristimo fiksne putanje da izbjegnemo konflikte sa ID-evima
    ruta = "confirm-old-step" if tip == "stari" else "confirm-new-step"
    link = f"{BASE_URL}/users/{ruta}/{token}"
    
    tekst = f"Kliknite na link za potvrdu promjene ({tip} email): {link}"
    poruka = MIMEText(tekst)
    poruka['to'] = email
    poruka['subject'] = "Verifikacija promjene emaila"
    
    raw_message = base64.urlsafe_b64encode(poruka.as_bytes()).decode()
    try:
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()
    except Exception as e:
        print(f"Greška pri slanju: {e}")



# Korak 1: Zahtjev za promjenu (new_email šalješ kao običan tekst u Swaggeru)
@router.post("/change-email-request")
async def request_email_change(
    new_email: str, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # Provjera baze (koristi tvoj models.User)
    if db.query(models.User).filter(models.User.email == new_email).first():
        raise HTTPException(status_code=400, detail="Email je već u upotrebi.")

    t_old = str(uuid.uuid4()) # Generišemo token za stari mail
    t_new = str(uuid.uuid4()) # generišem token za novi mail

    # Upis u tvoj EmailChangeRequest model
    zahtjev = models.EmailChangeRequest(
        user_id=current_user.id,
        new_email=new_email,
        token_old_email=t_old,
        token_new_email=t_new,
        is_old_email_confirmed=False,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db.add(zahtjev)
    db.commit()

    # Šaljemo na TRENUTNI mail korisnika
    posalji_mail_za_promjenu(current_user.email, t_old, "stari")
    return {"message": "Potvrda poslana na vaš stari email."}

# Korak 2: Potvrda na starom mailu
@router.get("/confirm-old-step/{token}")
async def confirm_old_step(token: str, db: Session = Depends(get_db)):
    req = db.query(models.EmailChangeRequest).filter(models.EmailChangeRequest.token_old_email == token).first()
    
    if not req or req.is_old_email_confirmed:
        raise HTTPException(status_code=400, detail="Token nevažeći ili iskorišten.")

    req.is_old_email_confirmed = True
    db.commit()

    # Šaljemo na NOVI mail
    posalji_mail_za_promjenu(req.new_email, req.token_new_email, "novi")
    return {"message": "Stari mail potvrđen. Provjerite novi mail za kraj."}

# Korak 3: Finalna potvrda i promjena u tabeli 'users'
@router.get("/confirm-new-step/{token}")
async def confirm_new_step(token: str, db: Session = Depends(get_db)):
    req = db.query(models.EmailChangeRequest).filter(models.EmailChangeRequest.token_new_email == token).first()
    
    if not req or not req.is_old_email_confirmed:
        raise HTTPException(status_code=400, detail="Niste potvrdili stari mail.")

    korisnik = db.query(models.User).filter(models.User.id == req.user_id).first()
    
    # Spremanje u EmailHistory (tvoj model)
    history = models.EmailHistory(
        user_id=korisnik.id, 
        old_email=korisnik.email,
        changed_at=datetime.now(timezone.utc)
    )
    db.add(history)

    # Konačna promjena
    korisnik.email = req.new_email
    
    # Brisanje privremenog zahtjeva
    db.delete(req)
    db.commit()

    return {"message": "Email je uspješno promijenjen!"}

from fastapi import Body

# promjena lozinke (samo vlasnik)
@router.post("/change-password")
async def change_password(
    old_password: str = Body(...), 
    new_password: str = Body(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. PROVJERA STARE LOZINKE
    # Upoređujemo unesenu staru lozinku sa onom iz baze (current_user.password_hash)
    is_password_correct = bcrypt.checkpw(
        old_password.encode('utf-8'), 
        current_user.password_hash.encode('utf-8')
    )
    
    if not is_password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Trenutna lozinka nije ispravna."
        )

    # 2. PROVJERA NOVE LOZINKE (da ne bude prazna)
    if not new_password or len(new_password) < 6:
        raise HTTPException(
            status_code=400, 
            detail="Nova lozinka mora imati najmanje 6 karaktera."
        )

    # 3. HASHIRANJE I SPAŠAVANJE
    current_user.password_hash = hash_password(new_password)
    db.commit()
    
    return {"message": "Lozinka je uspješno promijenjena!"}


# zaboravljena  lozinka
@router.post("/forgot-password")
async def forgot_password(email: str = Body(...), db: Session = Depends(get_db)):
    # 1. PRONALAŽENJE KORISNIKA
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Korisnik nije pronađen")
    # 2. GENERISANJE TOKENA ZA RESET
    token = create_jwt_token(
        data={"sub": user.email, "purpose": "password_reset"}, 
        expires_delta=timedelta(hours=1)
    )
    # 3. SLANJE MAILA SA LINKOM ZA RESET
    reset_link = f"{BASE_URL}/users/reset-password/{token}"
    message_text = f"Kliknite na link da resetirajte lozinku: {reset_link}"
    message = MIMEText(message_text)
    message['to'] = user.email
    message['subject'] = "Reset lozinke - Moja Prodavnica"
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service = get_gmail_service()
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        return {"message": "Link za reset lozinke poslan na vaš email."}
    except Exception as e:
        print(f"Greška pri slanju: {e}")
        raise HTTPException(status_code=500, detail="Greška pri slanju emaila.")

# reset lozinke
@router.post("/reset-password/{token}")
async def reset_password(token: str, nova_lozinka: str, db: Session = Depends(get_db)):
    try:
        # 1. Dekodiramo tvoj postojeći token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        # 2. Pronalazimo korisnika
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Korisnik nije pronađen")
        
        # 3. Upisujemo lozinku koju si proslijedio kao 'nova_lozinka'
        user.password_hash = hash_password(nova_lozinka)
        db.commit()
        
        return {"message": "Lozinka uspješno resetovana!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Token nije ispravan ili je istekao")
    
# dodavanje rola (vrsi samo admin) role moraju imati padajucu listu (buyer, seller, admin)
@router.post("/add-role/{user_id}")
async def add_role(user_id: int, role: str = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Samo admin može dodijeliti role")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Korisnik nije pronađen")

    # ne dozvoljene role su 
    if role not in ["buyer", "seller", "admin"]:
        raise HTTPException(status_code=400, detail="Nevažeća rola. Dozvoljene role su: buyer, seller, admin")
  
    user.role = models.UserRole(role)
    db.commit()
    return {"message": f"Role '{role}' dodijeljena korisniku {user.username}."}

    