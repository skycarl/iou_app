import logging
import os
from typing import Optional

import requests
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes
from telegram.ext.filters import MessageFilter

from app.iou.schema import User

logger = logging.getLogger(__name__)


X_TOKEN = os.environ['X_TOKEN']
HEADERS = {'X-Token': X_TOKEN}
base_url = os.environ.get('APP_URL')

def get_authorized_users():
    logger.debug('Fetching authorized users list from API')
    url = base_url + '/users/'
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        authorized_users = [User.model_validate(user) for user in response.json()]
        logger.debug(f'Successfully retrieved {len(authorized_users)} authorized users')
        return authorized_users
    except requests.exceptions.RequestException as e:
        logger.error(f'Error fetching authorized users: {e}')
        # If we can't connect to the API, return an empty list rather than crashing
        return []

def get_registered_chat_id(username: str) -> Optional[str]:
    """
    Call the GET /users/{username} API endpoint and return the conversation_id.
    Returns None if the user is not found.
    """
    url = f"{base_url}/users/{username}"
    try:
        logger.info(f"Checking registration status for user @{username}")
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            data = response.json()
            conversation_id = data.get('conversation_id')
            if conversation_id:
                logger.info(f"User @{username} is registered with conversation_id {conversation_id}")
            else:
                logger.info(f"User @{username} exists but is not registered (no conversation_id)")
            return conversation_id
        elif response.status_code == 404:
            logger.info(f"User @{username} is not found in the system")
            return None
        else:
            logger.error(f"Unexpected status code {response.status_code} when checking registration for @{username}")
            return None
    except Exception as e:
        logger.error(f"Error fetching registration for @{username}: {e}")
    return None

class AuthorizedUserFilter(MessageFilter):
    def filter(self, message):
        """Return True if the message should be allowed; False otherwise."""
        user = message.from_user
        if not user:
            logger.warning('Received message without user information')
            return False

        username = user.username
        authorized_user_list = [x.username for x in get_authorized_users()]
        is_authorized = username in authorized_user_list

        if is_authorized:
            logger.info(f"User @{username} passed authorization check")
        else:
            logger.warning(f"User @{username} failed authorization check")
        return is_authorized

async def handle_unauthorized_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user = update.message.from_user
        username = user.username if user and user.username else 'unknown_user'
        chat_id = update.message.chat_id
        message_text = update.message.text

        if update.message.chat.type == ChatType.GROUP:
            logger.warning(
                f'Unauthorized group chat access denied for @{username} '
                f'in chat {chat_id}. Command: {message_text}'
            )
            await update.message.reply_text('Sorry, you are not authorized to use this bot.')
        elif update.message.chat.type == ChatType.PRIVATE:
            logger.warning(f'Unauthorized private chat access denied for @{username}. Command: {message_text}')
            await update.message.reply_text('Sorry, you are not authorized to use this bot.')
        else:
            logger.warning(
                f'Unauthorized access denied for @{username} '
                f'in chat type {update.message.chat.type}. Command: {message_text}'
            )
            await update.message.reply_text('Sorry, you are not authorized to use this bot.')
    elif update.callback_query:
        user = update.callback_query.from_user
        username = user.username if user and user.username else 'unknown_user'
        query_data = update.callback_query.data

        logger.warning(f'Unauthorized callback query denied for @{username}. Query: {query_data}')
        await update.callback_query.answer(
            text='Unauthorized access!', show_alert=True
        )
