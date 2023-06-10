from typing import List
from fastapi import FastAPI, Depends, HTTPException
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


@app.get("/iou_status/", response_model=List[schemas.IOUStatus])
def read_iou_status(db: Session = Depends(get_db)):
    iou_status = crud.get_iou_status(db)
    return iou_status


# TODO this fails when there are no entries
@app.get("/max_sum_name/", response_model=schemas.IOUStatus)
def max_sum_name(db: Session = Depends(get_db)):
    name = crud.get_max_sum_name(db)
    return name

@app.delete("/delete/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = crud.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry = crud.delete_entry(db, entry)
    return {"detail": f"Entry {entry_id} deleted"}
