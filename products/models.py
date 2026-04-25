from database import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Float

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False) # Naziv 🏷️
    description = Column(String(500))         # Opis 📝
    price = Column(Float, nullable=False)     # Cijena 💰
    image_url = Column(String(255))           # Slika 🖼️
    
    # Ovo polje nam treba da bi baza znala koja je "sveska" u pitanju obuča, odjeća ili bijela tehnika
    product_type = Column(String(50)) 

    __mapper_args__ = {
        "polymorphic_identity": "product",
        "polymorphic_on": product_type,
    }


# Sada ćemo napraviti tri različite tabele koje nasljeđuju glavnu tabelu proizvoda. Svaka od njih će imati svoje specifične atribute, ali će dijeliti zajedničke atribute iz glavne tabele.
# obuča
class Footwear(Product):
    __tablename__ = "footwear"
    
    # Ovaj ID je i ključ ove tabele, ali i veza sa Glavnom knjigom
    id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    
    footwear_type = Column(String(50))  # Tene, Čizme...
    size = Column(Integer)             # Broj (npr. 42)
    gender = Column(String(20))        # Muška, Ženska...

    __mapper_args__ = {
        "polymorphic_identity": "footwear",
    }

# odjeća
class Clothing(Product):
    __tablename__ = "clothing"

    id = Column(Integer, ForeignKey("products.id"), primary_key=True)

    clothing_type = Column(String(50))  # Majica, Hlače...
    size = Column(String(10))             # S, M, L...
    gender = Column(String(20))        # Muška, Ženska...
    material = Column(String(50))      # Pamuk, Poliester...
    
    __mapper_args__ = {
        "polymorphic_identity": "clothing",
    }

#bjela tehnika
class HomeAppliance(Product):
    __tablename__ = "home_appliance"

    id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    appliance_type = Column(String(50))  # Frižider, Veš mašina...
    brand = Column(String(50))           # Samsung, LG...
    energy_rating = Column(String(10))   # A++, A+...
    
    __mapper_args__ = {
        "polymorphic_identity": "home_appliance",
    }

