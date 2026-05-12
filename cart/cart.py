import stripe
from dotenv import load_dotenv
import os
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
from database import SessionLocal
from . import models
from user.user import get_current_user
from sqlalchemy import func
from user.models import User  # Pretpostavljam da je ovdje User
from products.models import Product  # OVO VJEROVATNO NEDOSTAJE - Putanja do Product modela

# 1. Učitavamo podatke iz .env fajla
load_dotenv()
# 2. Povlačimo ključ koristeći os.getenv
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


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



# dodavanje proizvoda u korpu samo vlasnik može dodati proizvod u svoju korpu
@router.post('/add/{product_id}')
def add_to_cart(product_id: int, db: db_dependency, current_user: Annotated[int, Depends(get_current_user)]):
    # 1. Pronađi proizvod u bazi da vidiš koliko ga ima na stanju
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Proizvod nije pronađen")

    # 2. Provjeri da li korisnik već ima ovaj proizvod u korpi
    cart_item = db.query(models.CartItem).filter_by(user_id=current_user.id, product_id=product_id).first()

    # 3. Izračunaj koliko bi korisnik ukupno imao u korpi nakon ovog klika
    nova_kolicina = (cart_item.quantity + 1) if cart_item else 1

    # 4. KLJUČNA PROVJERA: Da li ta nova količina prelazi ono što imaš na stanju?
    if nova_kolicina > product.quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Nema dovoljno na stanju. Dostupno: {product.quantity}, Vi želite: {nova_kolicina}"
        )

    # 5. Ako je sve u redu, ažuriraj ili kreiraj stavku u korpi
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = models.CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.add(cart_item)

    # 6. Spasi promjene u bazu
    db.commit()
    
    return {
        "message": "Proizvod dodan u korpu", 
        "trenutno_u_korpi": nova_kolicina,
        "preostalo_na_stanju": product.quantity - nova_kolicina # Opciono, čisto da korisnik zna
    }



# 3. Kreiranje checkout sesije - ovdje ćemo poslati ukupnu sumu za cijelu korpu, a ne pojedinačne proizvode
@router.post('/create-checkout-session')
def create_checkout_session(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # 1. Dohvatamo SVE stavke iz baze za ovog korisnika
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Korpa je prazna")

    # 2. Računamo ukupnu cijenu (zbir svih proizvoda * njihova količina)
    total_cart_price = 0
    for item in cart_items:
        total_cart_price += item.quantity * item.product.price

    # 3. Primjenjujemo tvoju logiku popusta (preko 500 KM ide 15%)
    total_spent = db.query(func.sum(models.Order.total_price)).filter(models.Order.user_id == current_user.id).scalar() or 0
    user_discount = 0.15 if total_spent > 500 else 0.0
    
    # Ovo je iznos koji korisnik stvarno treba da plati
    final_price = total_cart_price * (1 - user_discount)

    # 4. Šaljemo Stripe-u JEDNU stavku koja predstavlja finalni račun
    line_items = [{
        'price_data': {
            'currency': 'bam',
            'product_data': {
                'name': 'Ukupno za platiti (Vaša korpa)',
            },
            # Stripe traži feninge (cio broj), zato zaokružujemo i množimo sa 100
            'unit_amount': int(round(final_price * 100)), 
        },
        'quantity': 1,
    }]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url='http://127.0.0.1:8000/cart/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://127.0.0.1:8000/cart/cancel',
        )
        return {"checkout_url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
    
    
# 4. Endpoint za uspjeh plaćanja - ovdje ćemo kasnije dodati logiku za kreiranje narudžbe, pražnjenje korpe i smanjenje zaliha
@router.get('/success')
def payment_success(session_id: str, db: Session = Depends(get_db)):
    try:
        # 1. Potvrda sa Stripe-a
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status != 'paid':
            raise HTTPException(status_code=400, detail="Plaćanje nije uspjelo.")

        customer_email = session.customer_details.email
        user = db.query(User).filter(User.email == customer_email).first()

        if not user:
            raise HTTPException(status_code=404, detail="Korisnik nije pronađen.")

        # 2. Uzimamo stvari iz korpe
        cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == user.id).all()

        # 3. Kreiramo Order koristeći tvoja stvarna polja (izbacio 'status')
        new_order = models.Order(
            user_id=user.id,
            total_price=session.amount_total / 100,
            payment_method="kartica",  # Ovo polje tvoj model zahtijeva
            discount_applied=0.0       # Ovdje možeš proslijediti iznos popusta ako ga pratiš
        )
        db.add(new_order)
        db.flush()

        # 4. Ažuriranje zaliha i brisanje korpe
        for item in cart_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.quantity -= item.quantity # Smanjujemo zalihe

            # Brisanje iz korpe
            db.delete(item)

        db.commit()
        return {"message": "Uspješno! Zalihe smanjene, korpa obrisana."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    

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