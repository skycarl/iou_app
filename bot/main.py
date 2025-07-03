"""Main module for IOU Bot."""
import logging
import os
from typing import Optional

import requests
from pydantic import ValidationError
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ApplicationBuilder
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from telegram.ext import filters
from telegram.ext import MessageHandler

from . import parse_exceptions
from .auth import AuthorizedUserFilter
from .auth import get_authorized_users
from .auth import handle_unauthorized_access
from .parse_exceptions import extract_api_error_message
from .parse_exceptions import extract_user_friendly_error
from app.iou.schema import IOUMessage
from app.iou.schema import IOUStatus
from app.iou.schema import SplitResponse
from app.iou.schema import SplitSchema
from app.iou.schema import TransactionEntry
from app.iou.schema import User

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
X_TOKEN = os.environ['X_TOKEN']
HEADERS = {'X-Token': X_TOKEN}
base_url = os.environ.get('APP_URL')
MAX_LEN = 4096

logging.basicConfig(
    format='[%(asctime)s][%(name)s][%(levelname)s][%(module)s:%(lineno)d] %(message)s',
    level=logging.INFO
)

logging.getLogger('app').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

authorized_filter = AuthorizedUserFilter()


async def get_chat_members(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    exclude_current_user: bool = False,
):
    users = set(x.username for x in get_authorized_users())
    if exclude_current_user:
        if update.message.chat.type == ChatType.GROUP:
            logger.debug(f'Excluding current user {update.message.from_user.username} from list')
            users -= {update.message.from_user.username}
        elif update.message.chat.type == ChatType.PRIVATE:
            logger.debug(f'Excluding current user {update.message.chat.username} from list')
            users -= {update.message.chat.username}
        else:
            logger.error('Unhandled chat type: %s', update.message.chat.type)
    return users


def add_entry(conversation_id, sender, recipient, amount, description):
    try:
        parsed_iou = IOUMessage(
            conversation_id=conversation_id,
            sender=sender,
            recipient=recipient,
            amount=amount,
            description=description,
        )
    except ValidationError as e:
        # Extract clean error message from Pydantic validation error
        clean_error = extract_user_friendly_error(e)
        logger.error(f"Pydantic validation error in add_entry: {clean_error}")
        raise parse_exceptions.AmountException(clean_error)
    except Exception as e:
        # For other exceptions, try to extract a clean message
        clean_error = extract_user_friendly_error(e)
        logger.error(f"Error in add_entry: {clean_error}")
        raise parse_exceptions.AmountException(clean_error)

    post_url = base_url + '/entries'
    logger.info(f'Posting to {post_url}: {parsed_iou.model_dump()}')
    response = requests.post(post_url, headers=HEADERS, json=parsed_iou.model_dump())
    return response, parsed_iou


async def get_iou_status_api_call(user1, user2):
    """Helper to call iou_status endpoint and return parsed response JSON or raise."""
    url = base_url + '/iou_status/?user1=' + str(user1) + '&user2=' + str(user2)
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        iou_status = IOUStatus.model_validate(response.json())
        logger.info(f'Got status: {iou_status.model_dump()}')
        return iou_status
    else:
        logger.error(f'Error attempting to get status: {response.text}')
        raise ValueError(response.text)


async def settle_api_call(user1, user2):
    """Helper to call settle endpoint and return parsed response JSON or raise."""
    url = base_url + '/settle?user1=' + str(user1) + '&user2=' + str(user2)
    response = requests.post(url, headers=HEADERS)
    if response.status_code == 200:
        settle_response = response.json()
        logger.info(f'Settle response: {settle_response}')
        return settle_response
    else:
        logger.error(f'Error attempting to settle: {response.text}')
        raise ValueError(response.text)


def chunk_buttons(buttons, chunk_size=3):
    """Return a list of button rows, each containing at most `chunk_size` buttons."""
    return [buttons[i:i + chunk_size] for i in range(0, len(buttons), chunk_size)]

# -----------------------------------------------------------------------------
# Helper functions for registration and notification
# -----------------------------------------------------------------------------
def get_registered_chat_id(username: str) -> Optional[str]:
    """
    Call the GET /users/{username} API endpoint and return the conversation_id.
    Returns None if the user is not found.
    """
    url = f"{base_url}/users/{username}"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            return data.get('conversation_id')
    except Exception as e:
        logger.error(f"Error fetching registration for @{username}: {e}")
    return None

async def notify_user(username: str, message: str, context: ContextTypes.DEFAULT_TYPE):
    """
    Notify a registered user by sending them a message to the conversation_id
    saved in the API.
    """
    chat_id = get_registered_chat_id(username)
    if chat_id:
        try:
            await context.bot.send_message(chat_id=int(chat_id), text=message)
        except Exception as e:
            logger.error(f"Failed to notify @{username}: {e}")
    else:
        logger.warning(f"User @{username} is not registered; cannot send notification.")

# -----------------------------------------------------------------------------
# /start command for user registration
# -----------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command by checking authorization and registering the user if necessary.
    """
    username = update.effective_user.username
    chat_id = update.effective_chat.id

    logger.info(f"User @{username} initiated /start command")

    if not username:
        await update.message.reply_text('You must have a Telegram username to use this bot.')
        return

    user_url = f"{base_url}/users/{username}"
    try:
        logger.info(f"Checking user @{username} authorization via API")
        get_response = requests.get(user_url, headers=HEADERS)
    except Exception as e:
        logger.error(f"Error fetching user data: {e}")
        await update.message.reply_text('An error occurred while checking your authorization.')
        return

    if get_response.status_code == 200:
        user_data = User.model_validate(get_response.json())
        # Check if conversation_id is already set
        if user_data.conversation_id is not None:
            logger.info(f"User @{username} is already registered")
            await update.message.reply_text('You are already registered.')
        else:
            # User is authorized but not registered; update conversation_id
            update_payload = {'conversation_id': str(chat_id)}
            try:
                logger.info(f"Registering user @{username} with conversation_id {chat_id}")
                put_response = requests.put(user_url, headers=HEADERS, json=update_payload)
                if put_response.status_code == 200:
                    logger.info(f"User @{username} registration successful")
                    await update.message.reply_text('Registration successful!')
                else:
                    logger.error(f"Failed to update user: {put_response.status_code} - {put_response.text}")
                    await update.message.reply_text('Registration failed due to an error.')
            except Exception as e:
                logger.error(f"Error updating user: {e}")
                await update.message.reply_text('Registration failed due to an error.')
    elif get_response.status_code == 404:
        # User not found in the database, so they are not authorized
        logger.info(f"Access denied to @{username}")
        await update.message.reply_text('You are not authorized to use this bot.')
    else:
        logger.error(f"Unexpected response: {get_response.status_code} - {get_response.text}")
        await update.message.reply_text('An error occurred. Please try again later.')


# ------------------------------------------------------------------------------------
# 1) Inline conversation entry points
# ------------------------------------------------------------------------------------

async def send_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username
    logger.info(f"User @{username} initiated /send command")

    possible_users = await get_chat_members(update, context, exclude_current_user=True)
    buttons = [InlineKeyboardButton(u, callback_data=f"SEND_RECIPIENT_{u}") for u in possible_users]
    keyboard = chunk_buttons(buttons, 3)
    msg = await update.message.reply_text(
        'Select a recipient:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['send_message_id'] = msg.message_id
    return ASKING_SEND_RECIPIENT


async def bill_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username
    logger.info(f"User @{username} initiated /bill command")

    possible_users = await get_chat_members(update, context, exclude_current_user=True)
    buttons = [InlineKeyboardButton(u, callback_data=f"BILL_SENDER_{u}") for u in possible_users]
    keyboard = chunk_buttons(buttons, 3)
    msg = await update.message.reply_text(
        'Select the user who owes you:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['bill_message_id'] = msg.message_id
    return ASKING_BILL_SENDER


async def query_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /query inline flow."""
    username = update.message.from_user.username
    logger.info(f"User @{username} initiated /query command")

    possible_users = await get_chat_members(
        update, context, exclude_current_user=False
    )
    buttons = [
        InlineKeyboardButton(username, callback_data=f"QUERY_USER1_{username}")
        for username in possible_users
    ]
    keyboard = [buttons]
    await update.message.reply_text(
        'Query: Select the first user:', reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASKING_QUERY_USER1


async def split_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /split inline flow."""
    username = update.message.from_user.username
    logger.info(f"User @{username} initiated /split command")

    possible_users = await get_chat_members(update, context, exclude_current_user=False)
    buttons = [
        InlineKeyboardButton(u, callback_data=f"SPLIT_PAYER_{u}")
        for u in possible_users
    ]
    keyboard = [buttons]
    msg = await update.message.reply_text(
        text='Select who paid the bill:',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    context.user_data['split_message_id'] = msg.message_id
    return ASKING_SPLIT_PAYER


async def settle_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /settle inline flow."""
    username = update.message.from_user.username
    logger.info(f"User @{username} initiated /settle command")

    possible_users = await get_chat_members(update, context, exclude_current_user=True)
    buttons = [
        InlineKeyboardButton(u, callback_data=f"SETTLE_USER_{u}")
        for u in possible_users
    ]
    keyboard = chunk_buttons(buttons, 3)
    msg = await update.message.reply_text(
        text='Select the user you want to settle with:',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    context.user_data['settle_message_id'] = msg.message_id
    return ASKING_SETTLE_USER


# ------------------------------------------------------------------------------------
# 2) Conversation States for inline flows
# ------------------------------------------------------------------------------------
(
    ASKING_SEND_AMOUNT,
    ASKING_SEND_RECIPIENT,
    ASKING_SEND_DESCRIPTION,
    ASKING_BILL_AMOUNT,
    ASKING_BILL_SENDER,
    ASKING_BILL_DESCRIPTION,
    ASKING_QUERY_USER1,
    ASKING_QUERY_USER2,
    ASKING_SPLIT_PAYER,
    ASKING_SPLIT_AMOUNT,
    ASKING_SPLIT_DESCRIPTION,
    ASKING_SPLIT_PARTICIPANTS,
    ASKING_SETTLE_USER,
    ASKING_SETTLE_CONFIRMATION,
) = range(14)


# ---- "Send" inline flow ----
async def ask_send_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text.strip()
    context.user_data['send_amount'] = amount_text
    message_id = context.user_data.get('send_message_id')
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=message_id,
        text=(
            f"----- Initiating send -----\n"
            f"Recipient: @{context.user_data['send_recipient']}\n"
            f"Amount: {amount_text}\n\nEnter a description:"
        )
    )
    return ASKING_SEND_DESCRIPTION


async def ask_send_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen_user = query.data.replace('SEND_RECIPIENT_', '')
    username = query.from_user.username
    logger.info(f"User @{username} selected recipient @{chosen_user} in /send flow")

    # Validate user
    if not get_registered_chat_id(chosen_user):
        logger.info(f"Recipient @{chosen_user} is not registered, aborting /send flow")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Recipient @{chosen_user} is not registered. They need to /start the bot first."
        )
        context.user_data.clear()
        return ConversationHandler.END
    context.user_data['send_recipient'] = chosen_user

    # Ask for the amount
    await query.edit_message_text(
        text=f"----- Initiating send -----\nRecipient: @{chosen_user}\n\nEnter the amount you want to send:"
    )
    return ASKING_SEND_AMOUNT


async def ask_send_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text.strip()
    context.user_data['send_description'] = description

    sender = update.message.from_user.username
    recipient = context.user_data['send_recipient']
    amount = context.user_data['send_amount']
    message_id = context.user_data.get('send_message_id')

    logger.info(f"User @{sender} completing /send flow to @{recipient} for ${amount} - '{description}'")

    try:
        logger.info(f"Creating new entry: @{sender} sending to @{recipient} for ${amount}")
        response, parsed_iou = add_entry(
            conversation_id=update.effective_chat.id,
            sender=sender,
            recipient=recipient,
            amount=amount,
            description=description,
        )
        if response.status_code == 201:
            logger.info(f"Successfully created entry for @{sender} sending to @{recipient}")
            # Edit the original message to show the conversation details with completed header
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=(
                        f"----- Initiated send -----\n"
                        f"Recipient: @{recipient}\n"
                        f"Amount: {parsed_iou.amount_str}\n"
                        f"Description: {description}"
                    )
                )
            # Send a new message with the final success text
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ You sent @{recipient} {parsed_iou.amount_str} for {description}"
            )
            # Notify the recipient in their own chat
            await notify_user(recipient, f"@{sender} sent you {parsed_iou.amount_str} for {description}", context)
        else:
            logger.error(f"API error creating entry: {response.status_code} - {response.text}")
            error_message = extract_api_error_message(response.text)
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=f"❌ Error: {error_message}\n\nTap here to try again: /send"
                )
    except parse_exceptions.AmountException as e:
        logger.error("Error in 'Send' flow (invalid amount): %s", e, exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}\n\nTap here to try again: /send")
    except Exception as e:
        logger.error("Error in 'Send' flow: %s", e, exc_info=True)
        error_message = extract_user_friendly_error(e)
        await update.message.reply_text(f"❌ Error: {error_message}\n\nTap here to try again: /send")
        if message_id:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text='Something went wrong.'
            )

    context.user_data.clear()
    return ConversationHandler.END


# ---- "Bill" inline flow ----
async def ask_bill_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text.strip()
    context.user_data['bill_amount'] = amount_text
    message_id = context.user_data.get('bill_message_id')
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=message_id,
        text=(
            f"----- Initiating bill -----\n"
            f"User: @{context.user_data['bill_sender']}\n"
            f"Amount: {amount_text}\n\nEnter a description:"
        )
    )
    return ASKING_BILL_DESCRIPTION


async def ask_bill_sender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen_user = query.data.replace('BILL_SENDER_', '')
    username = query.from_user.username
    logger.info(f"User @{username} selected sender @{chosen_user} in /bill flow")

    # Validate user
    if not get_registered_chat_id(chosen_user):
        logger.info(f"Sender @{chosen_user} is not registered, aborting /bill flow")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"User @{chosen_user} is not registered. They need to /start the bot first."
        )
        context.user_data.clear()
        return ConversationHandler.END
    context.user_data['bill_sender'] = chosen_user

    # Ask for the amount
    await query.edit_message_text(
        text=f"----- Initiating bill -----\nUser: @{chosen_user}\n\nEnter the amount you want to bill:"
    )
    return ASKING_BILL_AMOUNT


async def ask_bill_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text.strip()
    context.user_data['bill_description'] = description

    recipient = update.message.from_user.username  # the one doing the billing
    sender = context.user_data['bill_sender']      # the one who owes
    amount = context.user_data['bill_amount']
    message_id = context.user_data.get('bill_message_id')

    logger.info(f"User @{recipient} completing /bill flow to bill @{sender} for ${amount} - '{description}'")

    try:
        logger.info(f"Creating new entry: @{sender} owing @{recipient} for ${amount}")
        response, parsed_iou = add_entry(
            conversation_id=update.effective_chat.id,
            sender=sender,
            recipient=recipient,
            amount=amount,
            description=description,
        )
        if response.status_code == 201:
            logger.info(f"Successfully created bill entry for @{sender} owing @{recipient}")
            # Edit the original message to show the conversation details with completed header
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=(
                        f"----- Initiated bill -----\n"
                        f"User: @{sender}\n"
                        f"Amount: {parsed_iou.amount_str}\n"
                        f"Description: {description}"
                    )
                )
            # Send a new message with the final success text
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ You have billed @{sender} {parsed_iou.amount_str} for {description}"
            )
            # Notify the billed user
            await notify_user(sender, f"@{recipient} billed you {parsed_iou.amount_str} for {description}", context)
        else:
            logger.error(f"API error creating bill: {response.status_code} - {response.text}")
            error_message = extract_api_error_message(response.text)
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=f"❌ Error: {error_message}\n\nTap here to try again: /bill"
                )
    except parse_exceptions.AmountException as e:
        logger.error("Error in 'Bill' flow (invalid amount): %s", e, exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}\n\nTap here to try again: /bill")
    except Exception as e:
        logger.error("Error in 'Bill' flow: %s", e, exc_info=True)
        error_message = extract_user_friendly_error(e)
        await update.message.reply_text(f"❌ Error: {error_message}\n\nTap here to try again: /bill")
        if message_id:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text='Something went wrong.'
            )

    context.user_data.clear()
    return ConversationHandler.END


# ---- "Query" inline flow ----
async def ask_query_user1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen_user = query.data.replace('QUERY_USER1_', '')
    username = query.from_user.username
    logger.info(f"User @{username} selected first user @{chosen_user} in /query flow")

    # Validate user
    if not get_registered_chat_id(chosen_user):
        logger.info(f"User @{chosen_user} is not registered, aborting /query flow")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"User @{chosen_user} is not registered. They need to /start the bot first."
        )
        context.user_data.clear()
        return ConversationHandler.END
    context.user_data['query_user1'] = chosen_user
    possible_users = await get_chat_members(update, context, exclude_current_user=False)
    if chosen_user in possible_users:
        possible_users.remove(chosen_user)
    buttons = [InlineKeyboardButton(u, callback_data=f"QUERY_USER2_{u}") for u in possible_users]
    keyboard = chunk_buttons(buttons, 3)
    await query.edit_message_text(
        text=f"First user: @{chosen_user}. Now select the second user:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASKING_QUERY_USER2


async def ask_query_user2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen_user = query.data.replace('QUERY_USER2_', '')
    username = query.from_user.username

    # Validate user
    if not get_registered_chat_id(chosen_user):
        logger.info(f"Second user @{chosen_user} is not registered, aborting /query flow")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"User @{chosen_user} is not registered. They need to /start the bot first."
        )
        context.user_data.clear()
        return ConversationHandler.END
    context.user_data['query_user2'] = chosen_user

    user1 = context.user_data['query_user1']
    user2 = chosen_user
    logger.info(f"User @{username} querying IOU status between @{user1} and @{user2}")

    try:
        logger.info(f"Making API call to check IOU status between @{user1} and @{user2}")
        iou_status = await get_iou_status_api_call(user1, user2)
        logger.info(f"Query result: @{iou_status.owing_user} owes @{iou_status.owed_user} ${iou_status.amount}")
        # Format the amount nicely
        amount_str = f"${iou_status.amount:,.2f}"
        await query.edit_message_text(
            text=f"@{iou_status.owing_user} owes @{iou_status.owed_user} {amount_str}"
        )
    except ValueError as e:
        logger.error(f"Error attempting to query: {e}")
        error_message = extract_user_friendly_error(e)
        await query.edit_message_text(text=f"❌ Error: {error_message}")
    except Exception as e:
        logger.error("Error in 'Query' flow: %s", e, exc_info=True)
        error_message = extract_user_friendly_error(e)
        await query.edit_message_text(text=f"❌ Error: {error_message}")

    context.user_data.clear()
    return ConversationHandler.END


# ---- "Split" inline flow ----
async def split_payer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen_payer = query.data.replace('SPLIT_PAYER_', '')
    username = query.from_user.username
    logger.info(f"User @{username} selected payer @{chosen_payer} in /split flow")

    # Validate user
    if not get_registered_chat_id(chosen_payer):
        logger.info(f"Payer @{chosen_payer} is not registered, aborting /split flow")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Payer @{chosen_payer} is not registered. They need to /start the bot first."
        )
        context.user_data.clear()
        return ConversationHandler.END
    context.user_data['split_payer'] = chosen_payer
    await query.edit_message_text(
        text=f"----- Initiating split -----\nPayer: @{chosen_payer}\n\nEnter the amount:"
    )
    return ASKING_SPLIT_AMOUNT


async def split_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username
    amount_text = update.message.text.strip()
    payer = context.user_data['split_payer']
    logger.info(f"User @{username} entered amount ${amount_text} for split bill with payer @{payer}")

    context.user_data['split_amount'] = amount_text
    message_id = context.user_data.get('split_message_id')

    # Edit the existing message instead of creating a new one
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=message_id,
        text=(
            f"----- Initiating split -----\n"
            f"Payer: @{payer}\n"
            f"Amount: {amount_text}\n\n"
            f"Enter a description:"
        )
    )
    return ASKING_SPLIT_DESCRIPTION


async def split_description_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username
    desc_text = update.message.text.strip()
    payer = context.user_data['split_payer']
    amount = context.user_data['split_amount']

    logger.info(f"User @{username} entered description '{desc_text}' for split bill of ${amount} paid by @{payer}")

    context.user_data['split_description'] = desc_text

    # Initialize the participants set if it doesn't exist
    if 'split_participants' not in context.user_data:
        context.user_data['split_participants'] = set()

    # Automatically include both the initiating user and the payer in the participants
    initiating_user = update.message.from_user.username
    context.user_data['split_participants'].add(initiating_user)
    context.user_data['split_participants'].add(payer)

    await prompt_for_split_participants(update, context)
    return ASKING_SPLIT_PARTICIPANTS


def build_split_participants_keyboard(possible_users, selected_users):
    """
    Return an InlineKeyboardMarkup with one button per user to toggle them,
    plus a final 'Done' button.
    """
    buttons = []
    for user in possible_users:
        if user in selected_users:
            text = f"✅ {user}"
        else:
            text = f"⬜ {user}"
        buttons.append(InlineKeyboardButton(text, callback_data=f"TOGGLE_SPLIT_PARTICIPANT_{user}"))

    # TODO: May need to chunk the buttons into multiple rows
    keyboard_rows = [buttons]
    done_button = [InlineKeyboardButton('Done', callback_data='DONE_SPLIT_PARTICIPANTS')]
    keyboard_rows.append(done_button)

    return InlineKeyboardMarkup(keyboard_rows)


async def prompt_for_split_participants(update_or_query, context):
    """
    Sends/edits a message to prompt the user to select participants.
    This can be used both the first time or whenever toggling.
    """
    if 'split_participants' not in context.user_data:
        context.user_data['split_participants'] = set()

    all_users = await get_chat_members(update_or_query, context, exclude_current_user=False)
    selected_users = context.user_data['split_participants']
    kb = build_split_participants_keyboard(all_users, selected_users)

    text = (
        'Select participants (toggle by tapping). Currently selected:\n'
        f"{', '.join('@'+u for u in selected_users) if selected_users else '(none)'}"
    )

    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(text, reply_markup=kb)
    else:
        await update_or_query.edit_message_text(text, reply_markup=kb)


async def toggle_split_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_to_toggle = query.data.replace('TOGGLE_SPLIT_PARTICIPANT_', '')
    initiating_user = query.from_user.username
    payer = context.user_data['split_payer']

    # TODO remove this once we only display registered users
    if not get_registered_chat_id(user_to_toggle):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"User @{user_to_toggle} is not registered. They need to /start the bot first."
        )
        return ASKING_SPLIT_PARTICIPANTS

    participants_set = context.user_data.get('split_participants', set())

    # Check if user is trying to remove the payer
    if user_to_toggle == payer and user_to_toggle in participants_set:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"The payer @{payer} cannot be removed from the split."
        )
        return ASKING_SPLIT_PARTICIPANTS

    # Check if the user is trying to remove themselves
    elif user_to_toggle == initiating_user and user_to_toggle in participants_set:
        # Allow removal but inform the user
        participants_set.remove(user_to_toggle)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Heads up: You've removed yourself from the split. Did you mean to do that? "
                'You can re-select yourself if this was accidental.'
            )
        )
    elif user_to_toggle in participants_set:
        participants_set.remove(user_to_toggle)
    else:
        participants_set.add(user_to_toggle)

    context.user_data['split_participants'] = participants_set
    await prompt_for_split_participants(query, context)
    return ASKING_SPLIT_PARTICIPANTS


async def finish_split_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payer = context.user_data['split_payer']
    amount = context.user_data['split_amount']
    description = context.user_data['split_description']
    participants = list(context.user_data['split_participants'])
    initiating_user = query.from_user.username
    message_id = context.user_data.get('split_message_id')

    logger.info(
        f"User @{initiating_user} completing split bill flow: "
        f"payer=@{payer}, amount=${amount}, participants={participants}")

    # Ensure the payer is registered
    payer_chat_id = get_registered_chat_id(payer)
    if not payer_chat_id:
        logger.info(f"Payer @{payer} is not registered, aborting /split flow")
        await query.edit_message_text(
            f"Payer @{payer} is not registered. They need to /start the bot first."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Ensure all split participants are registered
    unregistered = []
    for user in participants:
        if not get_registered_chat_id(user):
            unregistered.append(user)
    if unregistered:
        logger.info(f"Some participants are not registered, aborting /split flow: {unregistered}")
        await query.edit_message_text(
            'The following users are not registered: ' +
            ', '.join('@' + u for u in unregistered) +
            '. They need to /start the bot first.'
        )
        context.user_data.clear()
        return ConversationHandler.END

    try:
        try:
            split_request = SplitSchema(
                conversation_id=str(query.message.chat_id),
                payer=payer,
                amount=amount,
                participants=participants,
                description=description,
            )
        except ValidationError as e:
            clean_error = extract_user_friendly_error(e)
            logger.error(f"Pydantic validation error in split flow: {clean_error}")
            raise parse_exceptions.AmountException(clean_error)
        except Exception as e:
            clean_error = extract_user_friendly_error(e)
            logger.error(f"Error creating SplitSchema: {clean_error}")
            raise parse_exceptions.AmountException(clean_error)

        post_url = base_url + '/split'
        logger.info(f"User @{initiating_user} creating split bill via API: {split_request.model_dump()}")

        response = requests.post(post_url, headers=HEADERS, json=split_request.model_dump())
        if response.status_code == 201:
            logger.info(f"User @{initiating_user} successfully created split bill")
            split_response = SplitResponse.model_validate(response.json())

            # Update the original message if it exists to show the completed split
            if message_id:
                participants_text = ', '.join('@' + p for p in participants)
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=(
                        f"----- Initiated split -----\n"
                        f"Payer: @{payer}\n"
                        f"Amount: {split_response.amount_str}\n"
                        f"Description: {description}\n"
                        f"Participants: {participants_text}"
                    )
                )

            # Update the participants selection message to show success
            await query.edit_message_text('✅ Split successful!')

            # Parse the response and send notifications
            participants_formatted = ', '.join('@' + u for u in participants)

            for user in participants:
                notification_message = (
                    f"💳 @{initiating_user} split a transaction!\n"
                    f"Payer: @{payer}\n"
                    f"Total amount: {split_response.amount_str}\n"
                    f"Split portion: {split_response.split_per_user_str}\n"
                    f"Description: {description}\n"
                    f"Participants: {participants_formatted}"
                )
                await notify_user(user, notification_message, context)
        else:
            logger.error(f"API error creating split: {response.status_code} - {response.text}")
            error_message = extract_api_error_message(response.text)
            await query.edit_message_text(f"❌ Error: {error_message}\n\nTap here to try again: /split")
    except parse_exceptions.AmountException as e:
        logger.error(f"Error in 'Split' flow (invalid amount): {e}", exc_info=True)
        await query.edit_message_text(f"❌ Error: {str(e)}\n\nTap here to try again: /split")
    except Exception as e:
        logger.error(f"Error in finish_split_participants: {e}", exc_info=True)
        error_message = extract_user_friendly_error(e)
        await query.edit_message_text(f"❌ Error: {error_message}\n\nTap here to try again: /split")

    context.user_data.clear()
    return ConversationHandler.END


# ---- "Settle" inline flow ----
async def ask_settle_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen_user = query.data.replace('SETTLE_USER_', '')
    username = query.from_user.username
    logger.info(f"User @{username} selected user @{chosen_user} for settlement")

    # Validate user
    if not get_registered_chat_id(chosen_user):
        logger.info(f"User @{chosen_user} is not registered, aborting /settle flow")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"User @{chosen_user} is not registered. They need to /start the bot first."
        )
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data['settle_other_user'] = chosen_user

    # Get IOU status between the two users
    try:
        logger.info(f"Getting IOU status between @{username} and @{chosen_user}")
        iou_status = await get_iou_status_api_call(username, chosen_user)

        # Check if there are any transactions to settle
        if iou_status.amount == 0:
            await query.edit_message_text(
                text=f"No outstanding transactions between you and @{chosen_user} to settle."
            )
            context.user_data.clear()
            return ConversationHandler.END

        context.user_data['settle_iou_status'] = iou_status
        amount_str = f"${iou_status.amount:,.2f}"

        buttons = [
            InlineKeyboardButton('✅ Yes, settle', callback_data='SETTLE_CONFIRM_YES'),
            InlineKeyboardButton('❌ No, cancel', callback_data='SETTLE_CONFIRM_NO')
        ]
        keyboard = [buttons]

        await query.edit_message_text(
            text=(
                f"💰 Settlement Summary:\n\n"
                f"@{iou_status.owing_user} owes @{iou_status.owed_user} {amount_str}\n\n"
                f"Are you sure you want to settle all transactions between you and @{chosen_user}? "
                f"This will erase all transaction history between you."
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ASKING_SETTLE_CONFIRMATION

    except ValueError as e:
        logger.error(f"Error getting IOU status for settlement: {e}")
        error_message = extract_user_friendly_error(e)
        await query.edit_message_text(text=f"❌ Error: {error_message}")
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in settle flow: {e}", exc_info=True)
        error_message = extract_user_friendly_error(e)
        await query.edit_message_text(text=f"❌ Error: {error_message}")
        context.user_data.clear()
        return ConversationHandler.END


async def ask_settle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    confirmation = query.data.replace('SETTLE_CONFIRM_', '')
    username = query.from_user.username
    other_user = context.user_data['settle_other_user']
    iou_status = context.user_data['settle_iou_status']

    if confirmation == 'NO':
        logger.info(f"User @{username} cancelled settlement with @{other_user}")
        await query.edit_message_text('Settlement cancelled.')
        context.user_data.clear()
        return ConversationHandler.END

    elif confirmation == 'YES':
        logger.info(f"User @{username} confirmed settlement with @{other_user}")

        try:
            # Call the settle API
            settle_response = await settle_api_call(username, other_user)
            transactions_settled = settle_response.get('transactions_settled', 0)

            if transactions_settled == 0:
                await query.edit_message_text(
                    text=f"No transactions were found to settle between {username} and {other_user}"
                )
            else:
                amount_str = f"${iou_status.amount:,.2f}"
                success_message = (
                    f"✅ Settlement completed!\n\n"
                    f"{transactions_settled} transaction(s) totaling {amount_str} have been settled "
                    f"between you and @{other_user}."
                )

                await query.edit_message_text(text=success_message)

                # Notify the other user
                other_user_message = (
                    f"✅ Settlement completed!\n\n"
                    f"@{username} has settled {transactions_settled} transaction(s) totaling {amount_str} "
                    f"between you. All transaction history has been cleared."
                )
                await notify_user(other_user, other_user_message, context)

                logger.info(
                    f"Successfully settled {transactions_settled} transactions "
                    f"between @{username} and @{other_user}")

        except ValueError as e:
            logger.error(f"Error calling settle API: {e}")
            error_message = extract_user_friendly_error(e)
            await query.edit_message_text(text=f"❌ Error: {error_message}")
        except Exception as e:
            logger.error(f"Error in settlement confirmation: {e}", exc_info=True)
            error_message = extract_user_friendly_error(e)
            await query.edit_message_text(text=f"❌ Error: {error_message}")

    context.user_data.clear()
    return ConversationHandler.END


# ------------------------------------------------------------------------------------
# Extra commands
# ------------------------------------------------------------------------------------
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text='Hello to yourself!'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            'To send money: /send (inline guided flow)\n\n'
            'To bill someone: /bill (inline guided flow)\n\n'
            'To check IOU status: /query (inline guided flow)\n\n'
            'To split a bill among multiple participants: /split (inline guided flow)\n\n'
            'To settle all transactions with another user: /settle (inline guided flow)'
        ),
    )


async def version(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response = requests.get(f"{base_url}/version", headers=HEADERS)
    api_version = response.json().get('version', 'Unknown')
    version_info = f"App version: {api_version}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=version_info)


async def list_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /list command to show all transactions for the current user.
    Fetches transactions from the backend and formats them for display.
    """
    username = update.effective_user.username

    # Call the /entries endpoint with the user's username as a filter
    url = f"{base_url}/entries?user1={username}"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            error_message = extract_api_error_message(response.text)
            await update.message.reply_text(f"❌ Error: {error_message}")
            return

        entries_data = response.json()
        if not entries_data:
            await update.message.reply_text('You have no transactions.')
            return

        validated_entries = []
        for entry_data in entries_data:
            try:
                entry = TransactionEntry.model_validate(entry_data)
                validated_entries.append(entry)
            except Exception as e:
                logger.error(f"Error validating entry: {e}", exc_info=True)

        if not validated_entries:
            await update.message.reply_text('Could not parse any transactions.')
            return

        # Format and display transactions
        formatted_entries = format_transactions(validated_entries, username)
        # Telegram message limit is 4096 characters
        for i in range(0, len(formatted_entries), MAX_LEN):
            await update.message.reply_text(formatted_entries[i:i+MAX_LEN])
        logger.info(f"User @{username} fetched transaction history")

    except Exception as e:
        logger.error(f"Error in list_transactions: {e}", exc_info=True)
        error_message = extract_user_friendly_error(e)
        await update.message.reply_text(f"❌ Error: {error_message}")


def format_transactions(entries, current_user):
    """
    Format transaction entries into a readable message.

    Args:
        entries: List of TransactionEntry models
        current_user: Username of the current user

    Returns:
        Formatted string with transaction details
    """
    if not entries:
        return 'No transactions found.'

    # Sort entries by timestamp
    entries.sort(key=lambda x: x.timestamp if x.timestamp else '')
    result = '📋 Your Transaction History:\n\n'

    for i, entry in enumerate(entries, 1):
        # Determine if user is sender or recipient to format accordingly
        if entry.sender == current_user:
            transaction = f"➖ You owe @{entry.recipient} {entry.amount_str}"
        else:
            transaction = f"➕ @{entry.sender} owes you {entry.amount_str}"

        result += f"{i}. {transaction}\n"
        if entry.description:
            result += f"   📝 {entry.description}\n"
        if entry.formatted_date:
            result += f"   📅 {entry.formatted_date}\n"
        result += '\n'

    return result


# ------------------------------------------------------------------------------------
# Register Handlers
# ------------------------------------------------------------------------------------
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(
        MessageHandler(filters.ALL & ~authorized_filter, handle_unauthorized_access)
    )

    # ---- "Send" conversation ----
    send_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('send', send_command_entry, filters=authorized_filter)
        ],
        states={
            ASKING_SEND_RECIPIENT: [
                CallbackQueryHandler(ask_send_recipient, pattern='^SEND_RECIPIENT_.*')
            ],
            ASKING_SEND_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_send_amount)
            ],
            ASKING_SEND_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_send_description)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    application.add_handler(send_conv_handler)

    # ---- "Bill" conversation ----
    bill_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('bill', bill_command_entry, filters=authorized_filter)
        ],
        states={
            ASKING_BILL_SENDER: [
                CallbackQueryHandler(ask_bill_sender, pattern='^BILL_SENDER_.*')
            ],
            ASKING_BILL_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_bill_amount)
            ],
            ASKING_BILL_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_bill_description)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    application.add_handler(bill_conv_handler)

    # ---- "Query" conversation ----
    query_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('query', query_command_entry, filters=authorized_filter)
        ],
        states={
            ASKING_QUERY_USER1: [
                CallbackQueryHandler(ask_query_user1, pattern='^QUERY_USER1_.*')
            ],
            ASKING_QUERY_USER2: [
                CallbackQueryHandler(ask_query_user2, pattern='^QUERY_USER2_.*')
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    application.add_handler(query_conv_handler)

    # ---- "Split" conversation ----
    split_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('split', split_command_entry, filters=authorized_filter)
        ],
        states={
            ASKING_SPLIT_PAYER: [
                CallbackQueryHandler(split_payer_callback, pattern='^SPLIT_PAYER_.*')
            ],
            ASKING_SPLIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, split_amount_callback)
            ],
            ASKING_SPLIT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, split_description_callback)
            ],
            ASKING_SPLIT_PARTICIPANTS: [
                CallbackQueryHandler(toggle_split_participant, pattern='^TOGGLE_SPLIT_PARTICIPANT_.*'),
                CallbackQueryHandler(finish_split_participants, pattern='^DONE_SPLIT_PARTICIPANTS$'),
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    application.add_handler(split_conv_handler)

    # ---- "Settle" conversation ----
    settle_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('settle', settle_command_entry, filters=authorized_filter)
        ],
        states={
            ASKING_SETTLE_USER: [
                CallbackQueryHandler(ask_settle_user, pattern='^SETTLE_USER_.*')
            ],
            ASKING_SETTLE_CONFIRMATION: [
                CallbackQueryHandler(ask_settle_confirmation, pattern='^SETTLE_CONFIRM_.*')
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    application.add_handler(settle_conv_handler)

    # ---- Additional handlers ----
    application.add_handler(CommandHandler('start', start))
    hello_handler = CommandHandler('hello', hello, filters=authorized_filter)
    application.add_handler(hello_handler)

    help_handler = CommandHandler('help', help_command, filters=authorized_filter)
    application.add_handler(help_handler)

    version_handler = CommandHandler('version', version, filters=authorized_filter)
    application.add_handler(version_handler)

    list_transactions_handler = CommandHandler('list', list_transactions, filters=authorized_filter)
    application.add_handler(list_transactions_handler)

    application.run_polling()
