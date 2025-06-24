# db/database.py

from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vibie.db")

# Create the SQLModel engine
engine = create_engine(DATABASE_URL, echo=True)

# Create all tables
def init_db():
    SQLModel.metadata.create_all(engine)

# Session generator
def get_session():
    with Session(engine) as session:
        yield session 