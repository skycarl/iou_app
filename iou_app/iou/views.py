import datetime
from typing import Any
from typing import List

import toml
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from iou_app.core.auth import verify_token
from iou_app.iou.ddb import create_user
from iou_app.iou.ddb import get_all_users
from iou_app.iou.ddb import get_entries as ddb_get_entries
from iou_app.iou.ddb import get_table
from iou_app.iou.ddb import get_user_by_username
from iou_app.iou.ddb import get_users_table
from iou_app.iou.ddb import update_user
from iou_app.iou.ddb import write_item_to_dynamodb
from iou_app.iou.schema import EntrySchema
from iou_app.iou.schema import IOUStatus
from iou_app.iou.schema import SplitSchema
from iou_app.iou.schema import User
from iou_app.iou.schema import UserUpdate

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
    user1: str = None,
    user2: str = None,
    table: Any = Depends(get_table)
):
    """
    Gets entries listed in the database with optional user filtering.

    - If no user parameters are provided, returns all entries
    - If only user1 is provided, returns entries where user1 is either sender or recipient
    - If both user1 and user2 are provided, returns only entries between these two users

    Returns:
        list: An array of Entry objects.
    """
    try:
        items = ddb_get_entries(table)
    except Exception as e:
        logger.error(f'Failed to get entries with error: {e}')
        raise HTTPException(status_code=400, detail='Failed to get entries')

    if not items:
        logger.info('No data found')
        raise HTTPException(status_code=404, detail='No data found.')

    entries = []
    try:
        for item in items:
            # Apply user filtering
            if user1 and user2:
                # Filter for transactions between user1 and user2 (in either direction)
                if not ((item['sender'] == user1 and item['recipient'] == user2) or
                        (item['sender'] == user2 and item['recipient'] == user1)):
                    continue
            elif user1:
                # Filter for transactions involving user1
                if not (item['sender'] == user1 or item['recipient'] == user1):
                    continue

            # Add the entry if it passes filters
            entry = EntrySchema(
                conversation_id=item['conversation_id'],
                sender=item['sender'],
                recipient=item['recipient'],
                amount=item['amount'],
                description=item['description'],
                timestamp=item['datetime']
            )
            entries.append(entry)
    except (ValidationError, KeyError) as e:
        logger.error(f'Invalid data in DynamoDB: {e}')
        raise HTTPException(status_code=400, detail='Invalid data in DynamoDB')

    return entries

@router.post('/entries', status_code=201)
async def add_entry(
    payload: EntrySchema,
    table: Any = Depends(get_table)
):
    """
    Add Entry in DynamoDB.

    Returns:
        Object: same payload which was sent with 201 status code on success.
    """
    payload.timestamp = datetime.datetime.now()

    item = {
        'datetime': payload.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'conversation_id': str(payload.conversation_id),
        'sender': payload.sender,
        'recipient': payload.recipient,
        'amount': str(payload.amount),
        'description': payload.description,
        'deleted': str(payload.deleted)
    }

    try:
        result = write_item_to_dynamodb(item, table)
    except Exception as e:
        logger.error(f'Failed to add entry: {payload} with error: {e}')
        raise HTTPException(status_code=400, detail='Failed to add entry')

    logger.success(f'Added entry: {result}')
    return payload

@router.get('/iou_status/', status_code=200)
async def read_iou_status(
    user1: str,
    user2: str,
    table: Any = Depends(get_table)
):
    entries = await get_entries(user1, user2, table)
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
async def split_amount(
    payload: SplitSchema,
    table: Any = Depends(get_table)
):
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
    participants_str = ', '.join(payload.participants)

    for participant in payload.participants:
        if participant != payload.payer:
            entry = EntrySchema(
                conversation_id=payload.conversation_id,
                sender=participant,
                recipient=payload.payer,
                amount=even_share,
                description=(f"Split: {payload.description} | "
                             f"Total: ${payload.amount:.2f} | "
                             f"Participants: {participants_str}"),
                deleted=False,
            )
            entries.append(entry)

    for entry in entries:
        await add_entry(entry, table)

    return {
        'message': 'Split successful',
        'amount': payload.amount,
        'split_per_user': even_share,
        'participants': payload.participants,
    }

@router.post('/users', status_code=201)
async def add_user(
    new_user: User,
    table: Any = Depends(get_users_table)
):
    """
    Add a new user. The username must be unique.
    """
    # Check if user exists
    existing_user = get_user_by_username(new_user.username, table)
    if existing_user:
        raise HTTPException(status_code=400, detail='User already exists')

    # Create user in DynamoDB
    user_data = new_user.model_dump()
    try:
        created_user = create_user(user_data, table)
        logger.success(f"Added user: {new_user.username}")
        return User(**created_user)
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=400, detail='Failed to create user')

@router.get('/users/{username}', status_code=200)
async def get_user(
    username: str,
    table: Any = Depends(get_users_table)
):
    """
    Retrieve a user's conversation_id by username.
    """
    user_data = get_user_by_username(username, table)
    if not user_data:
        raise HTTPException(status_code=404, detail='User not found')
    return {'username': user_data['username'], 'conversation_id': user_data.get('conversation_id')}

@router.put('/users/{username}', status_code=200)
async def update_user_endpoint(
    username: str,
    update: UserUpdate,
    table: Any = Depends(get_users_table)
):
    """
    Update a user's conversation_id.
    """
    # Check if user exists
    existing_user = get_user_by_username(username, table)
    if not existing_user:
        raise HTTPException(status_code=404, detail='User not found')

    # Update user in DynamoDB
    try:
        updated_user = update_user(username, update.model_dump(), table)
        logger.success(f"Updated user: {username} with new conversation_id: {update.conversation_id}")
        return User(**updated_user)
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        raise HTTPException(status_code=400, detail='Failed to update user')

@router.get('/users/', status_code=200, response_model=List[User])
async def get_users(table: Any = Depends(get_users_table)):
    """
    Retrieve all users.
    """
    try:
        users_data = get_all_users(table)
        return [User(**user) for user in users_data]
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=400, detail='Failed to get users')
