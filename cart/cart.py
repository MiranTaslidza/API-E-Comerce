from fastapi import APIRouter, Depends, status, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Annotated
from database import SessionLocal
from . import models
from user.user import get_current_user

from sqlalchemy import func

router = APIRouter(
    prefix='/cart',
    tags=['cart']
)

def get_db():
    db = SessionLocal() # otvaranje seseije
    try:
        yield db # privremeno proslijđivanje sesije
    finally:
        db.close() # zatvaranje sesije nakon korištenja 

db_dependency = Annotated[Session, Depends(get_db)] # dohvatanje podataka koje prosliđuje get_db funkcija

#prikaz  narudzbe samo vlasnik može vidjeti svoje narudzbe
# 1. Prikaz aktivne korpe sa logikom popusta
@router.get('/')
def get_cart(db: db_dependency, current_user: Annotated[any, Depends(get_current_user)]):
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    
    # Primjer logike lojalnosti: provjeravamo ukupnu historiju potrošnje
    total_spent = db.query(func.sum(models.Order.total_price)).filter(models.Order.user_id == current_user.id).scalar() or 0
    
    # Ako je potrošio više od 500 KM, dobija 15% popusta
    user_discount = 0.15 if total_spent > 500 else 0.0
    
    total_cart_price = 0
    for item in cart_items:
        # Ovdje pretpostavljamo da CartItem ima vezu ka proizvodu (item.product.price)
        total_cart_price += item.quantity * item.product.price

    # Primjena popusta na ukupnu sumu
    final_price = total_cart_price * (1 - user_discount)

    return {
        "items": cart_items,
        "total_before_discount": total_cart_price,
        "discount_percent": user_discount * 100,
        "final_price": final_price
    }

# 2. Pametno brisanje (smanjivanje količine)
@router.delete('/remove/{product_id}')
def remove_from_cart(product_id: int, db: db_dependency, current_user: Annotated[any, Depends(get_current_user)]):
    cart_item = db.query(models.CartItem).filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Proizvod nije u korpi")

    if cart_item.quantity > 1:
        # Smanji količinu za 1
        cart_item.quantity -= 1
    else:
        # Ako je zadnji komad, obriši ga potpuno
        db.delete(cart_item)
    
    db.commit()
    return {"message": "Količina ažurirana ili proizvod uklonjen"}

# dodavanje proizvoda u korpu samo vlasnik može dodati proizvod u svoju korpu
@router.post('/add/{product_id}')
def add_to_cart(product_id: int, db: db_dependency, current_user: Annotated[int, Depends(get_current_user)]):
    cart_item = db.query(models.CartItem).filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = models.CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.add(cart_item)
    db.commit()
    return {"message": "Product added to cart"}
