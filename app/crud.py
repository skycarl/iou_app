from sqlalchemy.orm import Session
from . import models, schemas
import datetime


def create_entry(db: Session, entry: schemas.EntryCreate):
    db_entry = models.Entry(
        sender=entry.sender,
        recipient=entry.recipient,
        amount=entry.amount,
        description=entry.description,
        datetime=datetime.datetime.now()
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


def get_entry(db: Session, entry_id: int):
    return db.query(models.Entry).filter(models.Entry.id == entry_id).first()


def get_entries(db: Session):
    return db.query(models.Entry).filter(models.Entry.deleted == False).all()


def get_pairs(db: Session, user1: str, user2: str):
    # query database for all entries that contain user1 or user2 as either sender or recipient
    user1_as_sender = db.query(models.Entry.sender,
                       models.Entry.recipient,
                       models.Entry.amount).filter(models.Entry.deleted == False).filter(models.Entry.sender == user1, models.Entry.recipient == user2).all()

    user2_as_sender = db.query(models.Entry.sender,
                       models.Entry.recipient,
                       models.Entry.amount).filter(models.Entry.deleted == False).filter(models.Entry.sender == user2, models.Entry.recipient == user1).all()   

    return user1_as_sender, user2_as_sender


def get_max_sum_name(db: Session):
    result = db.query(models.Entry.sender, models.Entry.amount).filter(models.Entry.deleted == False).group_by(models.Entry.sender).order_by(models.Entry.amount.desc()).first()
    if result:
        return {"sender": result[0], "amount": result[1]}
    return "No entries found"


def delete_entry(db: Session, entry: models.Entry):
    entry.deleted = True
    db.commit()
    db.refresh(entry)
    return entry
