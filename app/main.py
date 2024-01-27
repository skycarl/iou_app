import os

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware

from app.core.logger import init_logging
from app.core.main_router import router as main_router
from app.iou import iou_router

load_dotenv('.env')

root_router = APIRouter()

app = FastAPI(title='IOU App API')
app.add_middleware(DBSessionMiddleware, db_url=os.environ['DATABASE_URL'])

app.include_router(main_router)
app.include_router(iou_router)
app.include_router(root_router)

init_logging()

if __name__ == '__main__':
    # Use this for debugging purposes only
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8001, log_level='debug')
