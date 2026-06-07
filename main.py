from fastapi import FastAPI
from database import engine
from fastapi.staticfiles import StaticFiles
import user.models
from user.user import router as user_router

    
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
user.models.Base.metadata.create_all(bind=engine)

# # uključivanje routera
app.include_router(user_router)
