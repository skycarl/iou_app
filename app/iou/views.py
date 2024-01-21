import datetime
from typing import Optional
from loguru import logger
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import verify_token
from app.core.db.session import get_db
from app.iou.models import EntryModel
from app.iou.schema import EntrySchema
from app.iou import utils


router = APIRouter(dependencies=[Depends(verify_token)])


@router.get("/entries", status_code=200)
async def get_entries(
    conversation_id: int,
    db: Session = Depends(get_db)
    ):

    """
    Gets all the entries listed in the database for the specified conversation ID

    Returns:
        list: An array of Entry objects.
    """

    entries =  db.query(EntryModel).filter(
        EntryModel.deleted == False).filter(
            EntryModel.conversation_id == conversation_id).all()

    return entries

@router.post("/entries", status_code=201)
async def add_entry(payload: EntrySchema, db: Session = Depends(get_db)):

    """
    Add Entry in the database.

    Returns:
        Object: same payload which was sent with 201 status code on success.
    """

    db_entry = EntryModel(
        conversation_id=payload.conversation_id,
        sender=payload.sender,
        recipient=payload.recipient,
        amount=payload.amount,
        description=payload.description,
        datetime=datetime.datetime.now()
    )

    db.add(db_entry)
    db.commit()

    logger.success("Added an Entry")
    return payload


@router.put("/entries/{entry_id}", status_code=201)
async def update_entry(
    entry_id: int, payload: EntrySchema, db: Session = Depends(get_db)
):

    """
    Updates the Entry object in db

    Raises:
        HTTPException: 404 if entry_id is not found in the db

    Returns:
        object: updated Entry object with 201 status code
    """

    entry = db.query(EntryModel).filter(EntryModel.id == entry_id).first()
    if not entry:
        desc = "Entry not found"
        logger.error(desc)
        raise HTTPException(status_code=404, detail=desc)

    entry.conversation_id = payload.conversation_id
    entry.sender = payload.sender
    entry.recipient = payload.recipient
    entry.amount = payload.amount
    entry.description = payload.description
    entry.datetime = datetime.datetime.now()

    db.commit()

    logger.success("Updated an Entry.")
    return entry


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Deletes the Entry object from db

    Raises:
        HTTPException: 404 if entry_id is not found in the db

    Returns:
        Object: Deleted true with 204 status code
    """

    entry = db.query(EntryModel).filter(EntryModel.id == entry_id).first()
    if not entry:
        desc = "Entry not found"
        logger.error(desc)
        raise HTTPException(status_code=404, detail=desc)
    db.delete(entry)
    db.commit()

    logger.success("Deleted an Entry.")

    return {"Deleted": True}


@router.get("/iou_status/", status_code=200)
def read_iou_status(
    conversation_id,
    user1,
    user2,
    db: Session = Depends(get_db)
    ):

    # query database for all entries that contain user1 or user2 as either sender or recipient
    user1_as_sender = utils.query_for_user(db, user1, user2, int(conversation_id))
    user2_as_sender = utils.query_for_user(db, user2, user1, int(conversation_id)) # pylint: disable=arguments-out-of-order
    
    # TODO: refactor this to be more elegant. Maybe handle in the bot when we verify that the users are in the conversation?
    if user1_as_sender == user2_as_sender == []:
        iou_status = {"user1": user1, "user2": user2, "amount": 0.}
    else:
        iou_status = utils.compute_iou_status(user1_as_sender, user2_as_sender)
        
    return iou_status
