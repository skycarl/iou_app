
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


def test_get_max_sum_name(db):
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
    max_sum_name = crud.get_max_sum_name(db)
    assert max_sum_name['name'] == entry1.name

def test_get_entry(db, entry):
    created_entry = crud.create_entry(db, entry)
    retrieved_entry = crud.get_entry(db, created_entry.id)
    assert retrieved_entry.name == entry.name
    assert retrieved_entry.amount == entry.amount
    assert retrieved_entry.description == entry.description

def test_delete_entry(db, entry):
    created_entry = crud.create_entry(db, entry)
    deleted_entry = crud.delete_entry(db, created_entry)
    assert deleted_entry.deleted == True

def test_get_entries_with_deleted(db, entry):
    created_entry1 = crud.create_entry(db, entry)
    created_entry2 = crud.create_entry(db, entry)
    deleted_entry = crud.delete_entry(db, created_entry2)
    assert len(crud.get_entries(db)) == 1
    
