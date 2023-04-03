from app.schemas import EntryBase, EntryCreate, Entry, IOUStatus


def test_entry_base():
    entry_dict = {"name": "Alice", "amount": 23.99}
    entry = EntryBase(**entry_dict)
    assert entry.name == "Alice"
    assert entry.amount == 23.99
    assert entry.description is None


def test_entry_create():
    entry_dict = {"name": "Bob", "amount": 52.01, "description": "Brunch"}
    entry_create = EntryCreate(**entry_dict)
    assert entry_create.name == "Bob"
    assert entry_create.amount == 52.01
    assert entry_create.description == "Brunch"


def test_entry():
    entry_dict = {"id": 1, "name": "Groceries", "amount": 50.0}
    entry = Entry(**entry_dict)
    assert entry.id == 1
    assert entry.name == "Groceries"
    assert entry.amount == 50.0
    assert entry.description is None


def test_iou_status():
    iou_dict = {"name": "Sally", "amount": 50.0}
    iou_status = IOUStatus(**iou_dict)
    assert iou_status.name == "Sally"
    assert iou_status.amount == 50.0