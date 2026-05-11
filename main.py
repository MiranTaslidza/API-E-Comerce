from fastapi import FastAPI
from database import engine, Base # Uvezi Base direktno iz database
import products.models
import user.models
import wishlist.models

import cart.models # Ovo učitava klase CartItem i Order

from products.product import router as products_router
from user.user import router as user_router
from wishlist.wishlist import router as wishlist_router

from cart.cart import router as cart_router

app = FastAPI()

# Dovoljno je pozvati ovo JEDNOM. 
# SQLAlchemy će proći kroz sve uvezene modele koji koriste ovaj Base i napraviti tabele.
Base.metadata.create_all(bind=engine)

# uključivanje routera
app.include_router(user_router)
app.include_router(products_router)
app.include_router(wishlist_router)

app.include_router(cart_router)
