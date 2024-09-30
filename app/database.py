"""
Database definitions for web app
"""
from typing import Generator, Any
from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base: Any = declarative_base()


class User(Base):
    """ User definition """
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    active = Column(Boolean, default=True)


# Create the database tables
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """ return the database session """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
