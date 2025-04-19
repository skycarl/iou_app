import time
import uuid
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends
from loguru import logger

# In-memory cache for users
# Structure: {username: (user_data, expiry_timestamp)}
USER_CACHE = {}
# In-memory cache for entries
# Structure: {'all_entries': (entries_list, expiry_timestamp)}
ENTRIES_CACHE = {}
DEFAULT_CACHE_TTL = 3600


# Initialize DynamoDB resource
def get_dynamodb_resource():
    """Returns a DynamoDB resource."""
    return boto3.resource('dynamodb', region_name='us-west-2')


def get_table():
    """
    FastAPI dependency that provides a DynamoDB table.
    """
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table('iou_app')


def get_users_table():
    """
    FastAPI dependency that provides a DynamoDB table for users.
    """
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table('iou_users')


def get_all_users(table: Any = Depends(get_users_table)) -> List[Dict[str, Any]]:
    """
    Gets all users from the DynamoDB table.

    Args:
        table: DynamoDB table instance (injected by FastAPI)

    Returns:
        List of users.
    """
    try:
        response = table.scan()
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error retrieving users: {e}")
        raise Exception('Failed to retrieve users from DynamoDB') from e


def get_user_by_username(
    username: str, table: Any = Depends(get_users_table), ttl: int = DEFAULT_CACHE_TTL
) -> Optional[Dict[str, Any]]:
    """
    Gets a user by username from the DynamoDB table with caching.

    Args:
        username: The username to look up
        table: DynamoDB table instance (injected by FastAPI)
        ttl: Time-to-live for cache entry in seconds (default: 1 hour)

    Returns:
        User data if found, None otherwise.
    """
    current_time = time.time()

    # Check if user is in cache and not expired
    if username in USER_CACHE:
        user_data, expiry = USER_CACHE[username]
        if current_time < expiry:
            logger.info(f"Cache hit for user: {username}")
            return user_data
        else:
            logger.info(f"Cache expired for user: {username}")
            del USER_CACHE[username]

    # If not in cache or expired, query DynamoDB
    try:
        response = table.get_item(Key={'username': username})
        user_data = response.get('Item')

        # Store in cache if user found
        if user_data:
            expiry = current_time + ttl
            USER_CACHE[username] = (user_data, expiry)
            logger.info(f"Cached user: {username}, expires in {ttl} seconds")

        return user_data
    except ClientError as e:
        logger.error(f"Error retrieving user: {e}")
        raise Exception('Failed to retrieve user from DynamoDB') from e


def create_user(
    user_data: Dict[str, Any], table: Any = Depends(get_users_table)
) -> Dict[str, Any]:
    """
    Creates a new user in the DynamoDB table.

    Args:
        user_data: Dictionary containing user data
        table: DynamoDB table instance (injected by FastAPI)

    Returns:
        The created user data.
    """
    try:
        table.put_item(Item=user_data)
        # Update cache with new user
        username = user_data.get('username')
        if username:
            USER_CACHE[username] = (user_data, time.time() + DEFAULT_CACHE_TTL)
        return user_data
    except ClientError as e:
        logger.error(f"Error creating user: {e}")
        raise Exception('Failed to create user in DynamoDB') from e


def update_user(
    username: str, update_data: Dict[str, Any], table: Any = Depends(get_users_table)
) -> Dict[str, Any]:
    """
    Updates a user in the DynamoDB table.

    Args:
        username: The username to update
        update_data: Dictionary containing update data
        table: DynamoDB table instance (injected by FastAPI)

    Returns:
        The updated user data.
    """
    try:
        update_expression = 'SET ' + ', '.join(
            f"#{k} = :{k}" for k in update_data.keys()
        )
        expression_attribute_names = {f"#{k}": k for k in update_data.keys()}
        expression_attribute_values = {f":{k}": v for k, v in update_data.items()}

        response = table.update_item(
            Key={'username': username},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW',
        )

        # Update cache with latest data
        updated_user = response.get('Attributes')
        if updated_user:
            USER_CACHE[username] = (updated_user, time.time() + DEFAULT_CACHE_TTL)

        return updated_user
    except ClientError as e:
        logger.error(f"Error updating user: {e}")
        raise Exception('Failed to update user in DynamoDB') from e


# Function to invalidate cache for a specific user
def invalidate_user_cache(username: str):
    """
    Removes a user from the cache.

    Args:
        username: The username to remove from cache
    """
    if username in USER_CACHE:
        del USER_CACHE[username]
        logger.info(f"Cache invalidated for user: {username}")


# Function to clear the entire user cache
def clear_user_cache():
    """
    Clears the entire user cache.
    """
    USER_CACHE.clear()
    logger.info('User cache cleared')


# Function to invalidate the entries cache
def invalidate_entries_cache():
    """
    Invalidates the entire entries cache.
    """
    if 'all_entries' in ENTRIES_CACHE:
        del ENTRIES_CACHE['all_entries']
        logger.info('Entries cache invalidated')


# Function to clear the entire entries cache
def clear_entries_cache():
    """
    Clears the entire entries cache.
    """
    ENTRIES_CACHE.clear()
    logger.info('Entries cache cleared')


def write_item_to_dynamodb(item: dict, table: Any = Depends(get_table)):
    """
    Writes an item to the DynamoDB table 'iou_app'.

    The item dictionary must include a 'datetime' key.
    A new UUID will be generated and added as the 'id' attribute.

    Raises:
        ValueError: If 'datetime' is missing in the item.
        Exception: If the item fails to be written to DynamoDB.
    """
    if 'datetime' not in item:
        raise ValueError("The item must include a 'datetime' key.")

    item['id'] = str(uuid.uuid4())

    try:
        response = table.put_item(Item=item)
        # Invalidate entries cache since we added a new item
        invalidate_entries_cache()
        return response
    except ClientError as e:
        raise Exception('Failed to write item to DynamoDB') from e


def get_entries(table: Any = Depends(get_table)) -> List[Dict[str, Any]]:
    """
    Gets entries from the DynamoDB table.

    Args:
        table: DynamoDB table instance (injected by FastAPI)

    Returns:
        List of entries.
    """
    current_time = time.time()

    # Check if entries are in cache and not expired
    if 'all_entries' in ENTRIES_CACHE:
        entries_list, expiry = ENTRIES_CACHE['all_entries']
        if current_time < expiry:
            logger.info('Cache hit for entries')
            return entries_list
        else:
            logger.info('Cache expired for entries')
            invalidate_entries_cache()  # Use the invalidation function instead of direct deletion

    try:
        response = table.scan()
        entries_list = response.get('Items', [])

        # Store in cache if entries found
        if entries_list:
            expiry = current_time + DEFAULT_CACHE_TTL
            ENTRIES_CACHE['all_entries'] = (entries_list, expiry)
            logger.info(f"Cached entries, expires in {DEFAULT_CACHE_TTL} seconds")

        return entries_list
    except ClientError as e:
        logger.error(f"Error retrieving entries: {e}")
        raise Exception('Failed to retrieve entries from DynamoDB') from e


def update_item(
    item_id: str,
    update_expression: str,
    expression_attribute_values: Dict[str, Any],
    table: Any = Depends(get_table),
):
    """
    Updates an item in the DynamoDB table.

    Args:
        item_id: The ID of the item to update.
        update_expression: The update expression.
        expression_attribute_values: The expression attribute values.
        table: DynamoDB table instance (injected by FastAPI)

    Returns:
        The response from DynamoDB.
    """
    try:
        response = table.update_item(
            Key={'id': item_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='UPDATED_NEW',
        )
        # Invalidate entries cache since we updated an item
        invalidate_entries_cache()
        return response
    except ClientError as e:
        logger.error(f"Error updating item: {e}")
        raise Exception('Failed to update item in DynamoDB') from e


def delete_item(item_id: str, table: Any = Depends(get_table)):
    """
    Deletes an item from the DynamoDB table.

    Args:
        item_id: The ID of the item to delete.
        table: DynamoDB table instance (injected by FastAPI)

    Returns:
        The response from DynamoDB.
    """
    try:
        response = table.delete_item(Key={'id': item_id}, ReturnValues='ALL_OLD')
        # Invalidate entries cache since we deleted an item
        invalidate_entries_cache()
        return response
    except ClientError as e:
        logger.error(f"Error deleting item: {e}")
        raise Exception('Failed to delete item from DynamoDB') from e
