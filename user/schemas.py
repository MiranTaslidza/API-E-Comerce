from pydantic import BaseModel, EmailStr
from typing import Optional
from .models import UserRole  # Uvezi Enum iz tvog models.py fajla

class UserCreate(BaseModel):
    # Obavezni podaci za registraciju
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    
    # Opcioni podaci (korisnik ne mora da ih pošalje odmah, default je None)
    address: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    date_of_birth: Optional[str] = None
    
    # Koristi Enum za validaciju uloge (Klijent može da bira rolu, npr. buyer ili seller)
    # Ali u bazi je default BUYER ako klijent ništa ne pošalje
    role: Optional[UserRole] = UserRole.BUYER 

    # Polja is_verified i is_active su UKLONJENA odavde jer ih kontroliše isključivo backend!
