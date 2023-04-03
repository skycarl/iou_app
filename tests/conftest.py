from app.database import SessionLocal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models
import pytest


# TODO unify testing approach with official way of testing FastAPI apps like test_main.py does
@pytest.fixture
def db(tmp_path):

    SQLALCHEMY_DATABASE_URL = f'sqlite:///{tmp_path}/test_app.db'

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.Base.metadata.create_all(bind=engine)
    database = SessionLocal()
    return database
