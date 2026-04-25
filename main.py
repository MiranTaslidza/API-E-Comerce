from fastapi import FastAPI
from database import engine
from products.product import router as products_router
import products.models


app = FastAPI()
products.models.Base.metadata.create_all(bind=engine)


# uključivanje routera
app.include_router(products_router)
