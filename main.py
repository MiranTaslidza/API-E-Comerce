from fastapi import FastAPI
from database import engine

import user.models
from user.user import router as user_router


app = FastAPI()
user.models.Base.metadata.create_all(bind=engine)

# # uključivanje routera
app.include_router(user_router)
