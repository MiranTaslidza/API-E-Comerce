from fastapi import FastAPI
from database import engine
from fastapi.staticfiles import StaticFiles
import user.models
from user.user import router as user_router
from starlette.templating import Jinja2Templates
from fastapi import Request 
from user.user import get_current_user
from database import SessionLocal


templates = Jinja2Templates(directory="templates") # dodano za Jinja2  
app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")
user.models.Base.metadata.create_all(bind=engine)

# # uključivanje routera
app.include_router(user_router)


@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    token = request.cookies.get("access_token")
    request.state.user = None
    
    if token:
        db = SessionLocal() # Otvaramo sesiju ručno
        try:
            # Ovdje pozivamo tvoju funkciju
            # get_current_user zahtijeva (token, db)
            user = await get_current_user(token, db) 
            request.state.user = user
        except:
            request.state.user = None
        finally:
            db.close() # Obavezno zatvoriti
            
    response = await call_next(request)
    return response