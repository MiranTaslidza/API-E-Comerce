from sqlalchemy import Column, Integer, ForeignKey
from database import Base # Ako je database.py u istom nivou kao i folder wishlist

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    created_at = Column(Integer, nullable=False)  # Timestamp kada je proizvod dodat u wishlist