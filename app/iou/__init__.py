from fastapi import APIRouter

from app.iou.views import router

API_STR = '/api'

iou_router = APIRouter(prefix=API_STR)
iou_router.include_router(router)
