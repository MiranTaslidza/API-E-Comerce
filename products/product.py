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


# funkcija za prikaz svih proizvoda
@router.get('/', status_code=status.HTTP_200_OK)
async def read_all(db: db_dependency):
    return db.query(models.Product).all()


