from fastapi import FastAPI
from database import engine
from products.product import router as products_router
import products.models
import user.models
from user.user import router as user_router


app = FastAPI()
products.models.Base.metadata.create_all(bind=engine)
user.models.Base.metadata.create_all(bind=engine)


# uključivanje routera
app.include_router(products_router)
app.include_router(user_router)

