from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models
from . import schemas
from . import crud
from . import utils
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
def read_entries(conversation_id, db: Session = Depends(get_db)):
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Conversation ID not found")
    entries = crud.get_entries(db, conversation_id=conversation_id)
    return entries


@app.get("/iou_status/", response_model=schemas.IOUStatus)
def read_iou_status(conversation_id, user1, user2, db: Session = Depends(get_db)):
    q1, q2 = crud.get_pairs(db, int(conversation_id), user1, user2)
    iou_status = utils.compute_iou_status(q1, q2)
    return iou_status


@app.delete("/delete/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = crud.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry = crud.delete_entry(db, entry)
    return {"detail": f"Entry {entry_id} deleted"}
