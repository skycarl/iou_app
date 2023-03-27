
from app import crud, schemas
import pytest


@pytest.fixture
def entry(scope="session"):
    return schemas.EntryCreate(
        name="Alice",
        amount=100.00,
        description="A test entry"
    )


def test_create_entry(db, entry):
    created_entry = crud.create_entry(db, entry)
    assert created_entry.name == entry.name
    assert created_entry.amount == entry.amount
    assert created_entry.description == entry.description


def test_get_entries(db, entry):
    created_entry = crud.create_entry(db, entry)
    entries = crud.get_entries(db)
    assert len(entries) == 1
    assert entries[0].name == entry.name
    assert entries[0].amount == entry.amount
    assert entries[0].description == entry.description


def test_get_iou_status(db):
    entry1 = schemas.EntryCreate(
        name="Test Entry 1",
        amount=100.00,
        description="A test entry"
    )
    entry2 = schemas.EntryCreate(
        name="Test Entry 2",
        amount=50.00,
        description="Another test entry"
    )
    crud.create_entry(db, entry1)
    crud.create_entry(db, entry2)
    iou_status = crud.get_iou_status(db)
    assert len(iou_status) == 2
    assert iou_status[0].name == entry1.name
    assert iou_status[0].amount == entry1.amount
    assert iou_status[1].name == entry2.name
    assert iou_status[1].amount == entry2.amount
