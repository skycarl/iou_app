import pytest
from app.schemas import EntryBase, EntryCreate, Entry, IOUStatus


def test_entry_base():
    entry_dict = {"conversation_id": 0, "sender": "Alice", "recipient": "Bob", "amount": 23.99}
    entry = EntryBase(**entry_dict)
    assert entry.sender == "Alice"
    assert entry.recipient == "Bob"
    assert entry.amount == 23.99
    assert entry.description is None


def test_entry_base_negative_amount():
    entry_dict = {"conversation_id": 0, "sender": "Alice", "recipient": "Bob", "amount": -23.99}

    with pytest.raises(ValueError) as e:
        EntryBase(**entry_dict)

    assert 'Amount must be positive' in str(e.value)


def test_entry_create():
    entry_dict = {"conversation_id": 0, "sender": "Bob", "recipient": "Alice", "amount": 52.01, "description": "Brunch"}
    entry_create = EntryCreate(**entry_dict)
    assert entry_create.sender == "Bob"
    assert entry_create.recipient == "Alice"
    assert entry_create.amount == 52.01
    assert entry_create.description == "Brunch"


def test_entry():
    entry_dict = {"conversation_id": 0, "id": 1, "sender": "Alice", "recipient": "Bob", "amount": 23.99, "description": "Dinner"}
    entry = Entry(**entry_dict)
    assert entry.id == 1
    assert entry.sender == "Alice"
    assert entry.recipient == "Bob"
    assert entry.amount == 23.99
    assert entry.description == "Dinner"


def test_iou_status():
    iou_dict = {"user1": "Alice", "user2": "Bob", "amount": 50.0}
    iou_status = IOUStatus(**iou_dict)
    assert iou_status.user1 == "Alice"
    assert iou_status.user2 == "Bob"
    assert iou_status.amount == 50.0
