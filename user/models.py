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
    full_name = Column(String(255)) 
    address = Column(String(500)) 
    date_of_birth = Column(String(50)) # Može ostati String ili postati Date
    
    # Uloga koristi našu Enum klasu 👥
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.BUYER, nullable=False) 
    
    # Statusi (koristimo Boolean jer je lakše za rad u Pythonu) ✅❌
    is_verified = Column(Boolean, default=False) 
    is_active = Column(Boolean, default=True) 
    
    # Datumi (koristimo DateTime za lakše računanje vremena) 📅
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))