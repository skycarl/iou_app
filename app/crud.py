from sqlalchemy.orm import Session
from . import models, schemas
import datetime


def create_entry(db: Session, entry: schemas.EntryCreate):
    db_entry = models.Entry(
        name=entry.name,
        amount=entry.amount,
        description=entry.description,
        datetime=datetime.datetime.now()
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


def get_entries(db: Session):
    return db.query(models.Entry).all()
