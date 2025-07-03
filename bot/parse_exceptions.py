"""Custom exceptions for message parsing."""
from pydantic import ValidationError

class AmountException(Exception):
    """Exception raised when the amount is not a number."""
    pass

class ChatMemberException(Exception):
    """Exception raised when the chat member is not found."""
    pass

def extract_user_friendly_error(error: Exception) -> str:
    """
    Extract a user-friendly error message from various types of exceptions.

    Args:
        error: The exception to extract the message from

    Returns:
        A clean, user-friendly error message
    """
    if isinstance(error, ValidationError) and error.errors():
        # For Pydantic ValidationError, try to extract the first error's context
        first_error = error.errors()[0]
        if 'ctx' in first_error and 'error' in first_error['ctx']:
            # This extracts the original AmountException message
            return str(first_error['ctx']['error'])

    # For everything else, just return the string representation
    return str(error)

def extract_api_error_message(response_text: str) -> str:
    """
    Extract user-friendly error message from API response.

    Args:
        response_text: The response text from the API

    Returns:
        A clean error message for the user
    """
    try:
        import json
        data = json.loads(response_text)
        if isinstance(data, dict) and 'detail' in data:
            detail = data['detail']
            if isinstance(detail, list) and len(detail) > 0:
                first_detail = detail[0]
                if isinstance(first_detail, dict) and 'msg' in first_detail:
                    return first_detail['msg']
            elif isinstance(detail, str):
                return detail
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    # If we can't parse the JSON or extract a message, return the raw response
    return response_text
