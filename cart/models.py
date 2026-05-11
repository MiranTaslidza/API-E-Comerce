from sqlalchemy import Column, Integer, ForeignKey, Float, String
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base  

# Model za stavke u korpi
class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    
    # Automatski uzima trenutno vrijeme kao Integer (timestamp)
    created_at = Column(Integer, default=lambda: int(datetime.now().timestamp()))

    # Relacije (opciono, ali korisno)
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")

# Model za narudžbe
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_price = Column(Float, nullable=False)
    discount_applied = Column(Float, default=0.0)
    payment_method = Column(String(255), nullable=False) # "kartica" ili "pouzeće"
    
    # Automatski postavlja datum narudžbe
    order_date = Column(Integer, default=lambda: int(datetime.now().timestamp()))

    user = relationship("User", back_populates="orders")