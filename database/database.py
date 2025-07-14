import os
from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

# Importing models executes the module. This way, SQLModel knows to create the tables
# defined in the module in create_all.
from . import models

load_dotenv()

connect_args = {"check_same_thread": False}
engine = create_engine(os.getenv("TEST_DB_CONNECTION_STRING"), pool_size=10)

def create_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session