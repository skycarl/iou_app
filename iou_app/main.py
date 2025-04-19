from fastapi import APIRouter
from fastapi import FastAPI

from iou_app.core.logger import init_logging
from iou_app.core.main_router import router as main_router
from iou_app.iou.views import router as iou_router

root_router = APIRouter()

app = FastAPI(title='IOU App API')

app.include_router(main_router)
app.include_router(iou_router, prefix='/api')
app.include_router(root_router)

init_logging()

if __name__ == '__main__':
    # Use this for debugging purposes only
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8001, log_level='debug')
