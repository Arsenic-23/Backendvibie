from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vibie.db")

# Create the SQLModel engine
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

# Create all tables if they don't exist
def init_db():
    from db.models import User, Stream, Song  # ensure models are imported
    SQLModel.metadata.create_all(engine)

# Session generator
def get_session():
    with Session(engine) as session:
        yield session
