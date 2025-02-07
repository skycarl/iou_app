import os

from loguru import logger

from iou_app.iou.schema import UserDB


def load_user_db(file_path: str) -> UserDB:
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = f.read()
        try:
            return UserDB.model_validate_json(data)
        except Exception as e:
            logger.error(f"Failed to load user DB: {e}")
            return UserDB(users=[])
    return UserDB(users=[])
