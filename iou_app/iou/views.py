import datetime
import os
from typing import Callable
from typing import List
from typing import Optional

import toml
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from iou_app.core.auth import verify_token
from iou_app.iou.google_sheets import get_service
from iou_app.iou.schema import EntrySchema
from iou_app.iou.schema import IOUStatus
from iou_app.iou.schema import SplitSchema
from iou_app.iou.schema import User
from iou_app.iou.schema import UserUpdate
from iou_app.iou.user_db import load_user_db


SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
USER_DB_FILE = 'user_db.json'

user_db = load_user_db(USER_DB_FILE)
router = APIRouter(dependencies=[Depends(verify_token)])

def get_version():
    with open('pyproject.toml', 'r') as f:
        pyproject_data = toml.load(f)
    return pyproject_data['tool']['poetry']['version']

@router.get('/version')
async def get_version_endpoint():
    return {'version': get_version()}


@router.get('/entries', status_code=200)
async def get_entries(
    conversation_id: Optional[int] = None,
    service: Callable = Depends(get_service)
    ):

    """
    Gets all the entries listed in the database for the specified conversation ID

    Returns:
        list: An array of Entry objects.
    """

    sheet = service.spreadsheets()
    try:
        result = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range='Sheet1')
            .execute()
        )
        values = result.get('values', [])
    except Exception as e:
        logger.error(f'Failed to get entries with error: {e}')
        raise HTTPException(status_code=400, detail='Failed to get entries')

    if not values:
        logger.info(f'No data found with conversation_id: {conversation_id}')
        raise HTTPException(status_code=404, detail='No data found.')

    rows = values[1:]
    if conversation_id is not None:
        rows = [row for row in rows if row[1] == str(conversation_id)]

    entries = []
    try:
        for row in rows:
            entry = EntrySchema(
                conversation_id=row[1],
                sender=row[2],
                recipient=row[3],
                amount=row[4],
                description=row[5],
                timestamp=row[0]
            )
            entries.append(entry)
    except ValidationError:
        raise HTTPException(status_code=400, detail='Invalid data in Google Sheets')

    return entries

@router.post('/entries', status_code=201)
async def add_entry(payload: EntrySchema,
                    service: Callable = Depends(get_service)):

    """
    Add Entry in Google Sheets.

    Returns:
        Object: same payload which was sent with 201 status code on success.
    """

    sheet = service.spreadsheets()

    payload.timestamp = datetime.datetime.now()
    values = [
        [
            payload.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            payload.conversation_id,
            payload.sender,
            payload.recipient,
            payload.amount,
            payload.description,
            payload.deleted
        ]
    ]
    body = {
        'values': values
    }
    try:
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1',
            valueInputOption='RAW',
            body=body
        ).execute()
    except Exception as e:
        logger.error(f'Failed to add entry: {payload} with error: {e}')
        raise HTTPException(status_code=400, detail='Failed to add entry')

    logger.success(f'Added entry: {result}')
    return payload


@router.get('/iou_status/', status_code=200)
async def read_iou_status(
    user1: str,
    user2: str,
    conversation_id: Optional[int] = None,
    service: Callable = Depends(get_service)
):
    entries = await get_entries(conversation_id, service)
    total_user1_owes = sum(float(e.amount) for e in entries if e.sender == user1 and e.recipient == user2)
    total_user2_owes = sum(float(e.amount) for e in entries if e.sender == user2 and e.recipient == user1)
    difference = total_user1_owes - total_user2_owes

    if difference == 0:
        iou_status = IOUStatus(
            owing_user=user1,
            owed_user=user2,
            amount=0.0
        )
    elif difference > 0:
        iou_status = IOUStatus(
            owing_user=user1,
            owed_user=user2,
            amount=difference
        )
    else:
        iou_status = IOUStatus(
            owing_user=user2,
            owed_user=user1,
            amount=abs(difference)
        )

    logger.success(f'Fetched status: {iou_status}')
    return iou_status

@router.post('/split', status_code=201)
async def split_amount(payload: SplitSchema, service: Callable = Depends(get_service)):
    """
    Split an amount evenly among a list of participants.
    """
    num_participants = len(payload.participants)
    if num_participants < 2:
        return JSONResponse(
            status_code=400,
            content={'message': 'At least two participants are required for a split.'},
        )

    even_share = round(payload.amount / num_participants, 2)

    entries = []
    for participant in payload.participants:
        if participant != payload.payer:
            entry = EntrySchema(
                conversation_id=payload.conversation_id,
                sender=participant,
                recipient=payload.payer,
                amount=even_share,
                description=f"Split: {payload.description}",
                deleted=False,
            )
            entries.append(entry)

    for entry in entries:
        await add_entry(entry, service)

    return {
        'message': 'Split successful',
        'amount': payload.amount,
        'split_per_user': even_share,
        'participants': payload.participants,
    }

@router.post('/users', status_code=201)
async def add_user(new_user: User):
    """
    Add a new user. The username must be unique.
    """
    if any(u.username == new_user.username for u in user_db.users):
        raise HTTPException(status_code=400, detail='User already exists')
    user_db.users.append(new_user)
    user_db.save_to_disk(USER_DB_FILE)
    logger.success(f"Added user: {new_user.username}")
    return new_user

@router.get('/users/{username}', status_code=200)
async def get_user(username: str):
    """
    Retrieve a user's conversation_id by username.
    """
    for user in user_db.users:
        if user.username == username:
            return {'username': user.username, 'conversation_id': user.conversation_id}
    raise HTTPException(status_code=404, detail='User not found')

@router.put('/users/{username}', status_code=200)
async def update_user(username: str, update: UserUpdate):
    """
    Update a user's conversation_id.
    """
    for idx, user in enumerate(user_db.users):
        if user.username == username:
            # Update the conversation ID
            user_db.users[idx].conversation_id = update.conversation_id
            user_db.save_to_disk(USER_DB_FILE)
            logger.success(f"Updated user: {username} with new conversation_id: {update.conversation_id}")
            return user_db.users[idx]
    raise HTTPException(status_code=404, detail='User not found')


@router.get('/users/', status_code=200, response_model=List[User])
async def get_users():
    """
    Retrieve all users.
    """
    return user_db.users
