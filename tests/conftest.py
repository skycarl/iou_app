from app.database import SessionLocal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models
import pytest


# TODO think about whether I really need this here
@pytest.fixture
# def db(tmp_path, scope="session"):  # TODO think about this scope
def db(tmp_path):  # TODO think about this scope

    SQLALCHEMY_DATABASE_URL = f'sqlite:///{tmp_path}/test_app.db'

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.Base.metadata.create_all(bind=engine)
    database = SessionLocal()
    return database
