from datetime import datetime
from app.models import Entry


def test_entry_model():
    # Create an instance of Entry model
    entry = Entry(
        sender='Alice',
        amount=120.54,
        description='Dinner',
        datetime=datetime.now()
    )

    # Verify attributes of Entry model
    assert entry.sender == 'Alice'
    assert entry.amount == 120.54
    assert entry.description == 'Dinner'
    assert isinstance(entry.datetime, datetime)

    # Verify that the model has the expected table name
    assert Entry.__tablename__ == 'entries'

    # Verify that the model has the expected columns
    assert 'id' in Entry.__table__.columns
    assert 'datetime' in Entry.__table__.columns
    assert 'sender' in Entry.__table__.columns
    assert 'amount' in Entry.__table__.columns
    assert 'description' in Entry.__table__.columns
