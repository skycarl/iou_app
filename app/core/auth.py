import os

from fastapi import Header
from fastapi import HTTPException

X_TOKEN = os.environ.get('X_TOKEN', 'not-found')


async def verify_token(x_token: str = Header()):
    if x_token != X_TOKEN:
        raise HTTPException(status_code=400, detail='X-Token header invalid')
