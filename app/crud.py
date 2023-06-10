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


def get_entry(db: Session, entry_id: int):
    return db.query(models.Entry).filter(models.Entry.id == entry_id).first()


def get_entries(db: Session):
    return db.query(models.Entry).filter(models.Entry.deleted == False).all()


def get_iou_status(db: Session):
    return db.query(
        models.Entry.name,
        models.Entry.amount).filter(models.Entry.deleted == False).group_by(models.Entry.name).all()


def get_max_sum_name(db: Session):
    result = db.query(models.Entry.name, models.Entry.amount).filter(models.Entry.deleted == False).group_by(models.Entry.name).order_by(models.Entry.amount.desc()).first()
    return {"name": result[0], "amount": result[1]}


def delete_entry(db: Session, entry: models.Entry):
    entry.deleted = True
    db.commit()
    db.refresh(entry)
    return entry
