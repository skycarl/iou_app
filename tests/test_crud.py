
from app import crud, schemas
import pytest


@pytest.fixture
def entry1(scope="session"):
    return schemas.EntryCreate(
        conversation_id=0,
        sender="Alice",
        recipient="Bob",
        amount=100.00,
        description="A test entry"
    )

@pytest.fixture
def entry2():
    return schemas.EntryCreate(
        conversation_id=0,
        sender="Bob",
        recipient="Alice",
        amount=50.00,
        description="Another test entry"
    )

@pytest.fixture
def entry3():
    return schemas.EntryCreate(
        conversation_id=1,
        sender="Alice",
        recipient="Frank",
        amount=15.00,
        description="Test entry in different conversation"
    )


def test_create_entry(db, entry1):
    created_entry = crud.create_entry(db, entry1)
    assert created_entry.sender == entry1.sender
    assert created_entry.recipient == entry1.recipient
    assert created_entry.amount == entry1.amount
    assert created_entry.description == entry1.description


def test_get_entries(db, entry1):
    created_entry = crud.create_entry(db, entry1)
    entries = crud.get_entries(db, conversation_id=entry1.conversation_id)
    assert len(entries) == 1
    assert entries[0].sender == entry1.sender
    assert entries[0].recipient == entry1.recipient
    assert entries[0].amount == entry1.amount
    assert entries[0].description == entry1.description


def test_get_iou_status(db, entry1, entry2, entry3):
    
    crud.create_entry(db, entry1)
    crud.create_entry(db, entry2)
    crud.create_entry(db, entry3)
    iou_status = crud.get_pairs(db, conversation_id=entry1.conversation_id, user1=entry1.sender, user2=entry1.recipient)
    assert iou_status[0] == [('Alice', 'Bob', 100.0)]
    assert iou_status[1] == [('Bob', 'Alice', 50.0)]


def test_get_max_sum_name(db):
    entry1 = schemas.EntryCreate(
        conversation_id=0,
        sender="Alice",
        recipient="Bob",
        amount=100.00,
        description="A test entry"
    )
    entry2 = schemas.EntryCreate(
        conversation_id=0,
        sender="Fred",
        recipient="Linda",
        amount=50.00,
        description="Another test entry"
    )
    crud.create_entry(db, entry1)
    crud.create_entry(db, entry2)
    max_sum_name = crud.get_max_sum_name(db)
    assert max_sum_name['sender'] == entry1.sender

def test_get_entry(db, entry1):
    crud.create_entry(db, entry1)
    retrieved_entry = crud.get_entry(db, 1)
    assert retrieved_entry.sender == entry1.sender
    assert retrieved_entry.amount == entry1.amount
    assert retrieved_entry.description == entry1.description

def test_delete_entry(db, entry1):
    created_entry = crud.create_entry(db, entry1)
    deleted_entry = crud.delete_entry(db, created_entry)
    assert deleted_entry.deleted == True

def test_get_entries_with_deleted(db, entry1):
    created_entry1 = crud.create_entry(db, entry1)
    created_entry2 = crud.create_entry(db, entry1)
    deleted_entry = crud.delete_entry(db, created_entry2)
    assert len(crud.get_entries(db, conversation_id=entry1.conversation_id)) == 1
    
