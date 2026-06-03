import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLAlchemyEnum
from database import Base
from datetime import datetime, timezone

# 1. Definiramo listu dozvoljenih uloga
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SELLER = "seller"
    BUYER = "buyer"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Unikatni podaci za identifikaciju
    username = Column(String(50), unique=True, nullable=False, index=True) 
    email = Column(String(100), unique=True, nullable=False, index=True) 
    
    # Sigurnost
    password_hash = Column(String(255), nullable=False) 
    
    # Osnovni podaci
    first_name = Column(String(255)) 
    last_name = Column(String(255))
    address = Column(String(500)) 
    phone_number = Column(String(20)) 
    profile_picture = Column(String(255)) 
    state = Column(String(50)) # država u smislu administrativne jedinice (npr. država, pokrajina, kanton) - može biti opcionalno ako se ne koristi
    city = Column(String(50))  # grad
    country = Column(String(50))  # država označava državu u smislu nezavisne zemlje (npr. Hrvatska, Bosna i Hercegovina, Njemačka).
    zip_code = Column(String(10)) 
    date_of_birth = Column(String(50)) # Može ostati String ili postati Date
    
    # Uloga koristi našu Enum klasu 👥
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.BUYER, nullable=False) 
    
    # Statusi (koristimo Boolean jer je lakše za rad u Pythonu) ✅❌
    is_verified = Column(Boolean, default=False) 
    is_active = Column(Boolean, default=True) 
    
    # Datumi (koristimo DateTime za lakše računanje vremena) 📅
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class EmailChangeRequest(Base):
    __tablename__ = "email_change_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False) # Ovdje pamtimo ID korisnika
    new_email = Column(String(100), nullable=False)
    
    # Tokeni za potvrdu starog i novog maila
    token_old_email = Column(String(255), nullable=False)
    token_new_email = Column(String(255), nullable=False)
    
    # Status i vrijeme isteka
    is_old_email_confirmed = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)

# 📜 Povijest promjena e-maila
class EmailHistory(Base):
    __tablename__ = "email_history"

    id = Column(Integer, primary_key=True, index=True) # Unikatni ID za svaki zapis
    user_id = Column(Integer, nullable=False, index=True) # ID korisnika (može se ponavljati)
    old_email = Column(String(100), nullable=False)
    changed_at = Column(DateTime, default=datetime.now)

