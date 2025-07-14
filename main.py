import logging;

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import create_db
from services.schedule import router as schedule_router

# Reduce logging
uvicorn_error = logging.getLogger("uvicorn.access")
uvicorn_error.disabled = True

app = FastAPI()

# Whitelist connection from frontend
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include sub-routers
app.include_router(schedule_router.router)

@app.on_event("startup")
def on_startup():
    create_db()

@app.get("/")
async def root():
    return {"Welcome to Orca Service!"}