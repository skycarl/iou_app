from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db
from app import crud, schemas
from app.database import engine, Base

import pytest
import tempfile


@pytest.fixture
def entries():
    return [
        schemas.EntryCreate(sender="Jane Smith", amount=100.0,
                            description="Test entry 1"),
        schemas.EntryCreate(sender="John Doe", amount=50.0,
                            description="Test entry 2")
    ]


# TODO: Handle the database setup in a pytest fixture
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_create_entries(db: Session, entries):
    created_entries = []
    for entry in entries:
        created_entry = crud.create_entry(db=db, entry=entry)
        created_entries.append(created_entry)
        response = client.post("/entries/", json=entry.dict())
        assert response.status_code == 200

        created_entry = response.json()
        assert created_entry["sender"] == entry.sender
        assert created_entry["amount"] == entry.amount
        assert created_entry["description"] == entry.description
        assert "id" in created_entry


def test_read_entries(db: Session, entries):
    response = client.get("/entries/")
    assert response.status_code == 200
    retrieved_entries = response.json()
    assert len(retrieved_entries) == len(entries)
    for i, entry in enumerate(entries):
        assert retrieved_entries[i]["sender"] == entry.sender
        assert retrieved_entries[i]["amount"] == entry.amount
        assert retrieved_entries[i]["description"] == entry.description


def test_read_iou_status(db: Session, entries):
    response = client.get("/iou_status/")
    assert response.status_code == 200
    iou_status = response.json()
    assert len(iou_status) == 2
    assert iou_status[0]["sender"] == entries[0].sender
    assert iou_status[0]["amount"] == entries[0].amount
    assert iou_status[1]["sender"] == entries[1].sender
    assert iou_status[1]["amount"] == entries[1].amount


# Temporary workaround for database cleanup
def test_cleanup():
    Base.metadata.drop_all(bind=engine)
