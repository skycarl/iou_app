import datetime
import os
from typing import Callable
from typing import Optional

import toml
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from pydantic import ValidationError

from app.core.auth import verify_token
from app.iou import utils
from app.iou.google_sheets import get_service
from app.iou.schema import EntrySchema


SPREADSHEET_ID = os.environ['SPREADSHEET_ID']

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

    user1_as_sender = [entry for entry in entries if entry.sender == user1 and entry.recipient == user2]
    user2_as_sender = [entry for entry in entries if entry.sender == user2 and entry.recipient == user1]

    if user1_as_sender == user2_as_sender == []:
        iou_status = {'user1': user1, 'user2': user2, 'amount': 0.}
    else:
        iou_status = utils.compute_iou_status(user1_as_sender, user2_as_sender)

    logger.success(f'Fetched status: {iou_status}')

    return iou_status
