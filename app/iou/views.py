import datetime
import os
from typing import Callable
from typing import Optional

import toml
from fastapi import APIRouter
from fastapi import Depends
from loguru import logger

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
    version = get_version()
    return {'version': version}


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
    result = (
        sheet.values()
        .get(spreadsheetId=SPREADSHEET_ID, range='Sheet1')
        .execute()
    )
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return

    rows = values[1:]
    if conversation_id is not None:
        rows = [row for row in rows if row[1] == str(conversation_id)]

    entries = []
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
    result = sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1',
        valueInputOption='RAW',
        body=body
    ).execute()

    logger.success(f'Added entry: {payload} with result: {result}')
    return payload


@router.get('/iou_status/', status_code=200)
async def read_iou_status(
    conversation_id,
    user1,
    user2,
    service: Callable = Depends(get_service)
    ):

    entries = await get_entries(conversation_id, service)

    user1_as_sender = [entry for entry in entries if entry.sender == user1 and entry.recipient == user2]
    user2_as_sender = [entry for entry in entries if entry.sender == user2 and entry.recipient == user1]

    if user1_as_sender == user2_as_sender == []:
        iou_status = {'user1': user1, 'user2': user2, 'amount': 0.}
    else:
        iou_status = utils.compute_iou_status(user1_as_sender, user2_as_sender)

    return iou_status
