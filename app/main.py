from typing import List
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from . import models
from . import schemas
from . import crud
from .database import SessionLocal, engine


models.Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/entries/", response_model=schemas.Entry)
def create_entry(entry: schemas.EntryCreate, db: Session = Depends(get_db)):
    return crud.create_entry(db=db, entry=entry)


@app.get("/entries/", response_model=list[schemas.Entry])
def read_entries(db: Session = Depends(get_db)):
    entries = crud.get_entries(db)
    return entries


@app.get("/ledger_status/", response_model=List[schemas.LedgerStatus])
def read_ledger_status(db: Session = Depends(get_db)):
    ledger_status = crud.get_ledger_status(db)
    return ledger_status
