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


def get_iou_status(db: Session):
    query = db.query(models.Entry.name, models.Entry.amount) \
              .group_by(models.Entry.name) \
              .with_entities(models.Entry.name, models.func.sum(models.Entry.amount))
    result = []
    for row in query:
        result.append({'name': row[0], 'amount': row[1]})
    return [schemas.IOUStatus(name=row['name'], amount=row['amount']) for row in result]
