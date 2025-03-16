import uuid
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends
from loguru import logger

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

def get_user_by_username(username: str, table: Any = Depends(get_users_table)) -> Optional[Dict[str, Any]]:
    """
    Gets a user by username from the DynamoDB table.

    Args:
        username: The username to look up
        table: DynamoDB table instance (injected by FastAPI)

    Returns:
        User data if found, None otherwise.
    """
    try:
        response = table.get_item(
            Key={'username': username}
        )
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Error retrieving user: {e}")
        raise Exception('Failed to retrieve user from DynamoDB') from e

def create_user(user_data: Dict[str, Any], table: Any = Depends(get_users_table)) -> Dict[str, Any]:
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
        return user_data
    except ClientError as e:
        logger.error(f"Error creating user: {e}")
        raise Exception('Failed to create user in DynamoDB') from e

def update_user(username: str, update_data: Dict[str, Any], table: Any = Depends(get_users_table)) -> Dict[str, Any]:
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
        update_expression = 'SET ' + ', '.join(f"#{k} = :{k}" for k in update_data.keys())
        expression_attribute_names = {f"#{k}": k for k in update_data.keys()}
        expression_attribute_values = {f":{k}": v for k, v in update_data.items()}

        response = table.update_item(
            Key={'username': username},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        return response.get('Attributes')
    except ClientError as e:
        logger.error(f"Error updating user: {e}")
        raise Exception('Failed to update user in DynamoDB') from e

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
    try:
        response = table.scan()
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error retrieving entries: {e}")
        raise Exception('Failed to retrieve entries from DynamoDB') from e

def update_item(item_id: str,
                update_expression: str,
                expression_attribute_values: Dict[str, Any],
                table: Any = Depends(get_table)):
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
            ReturnValues='UPDATED_NEW'
        )
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
        response = table.delete_item(
            Key={'id': item_id},
            ReturnValues='ALL_OLD'
        )
        return response
    except ClientError as e:
        logger.error(f"Error deleting item: {e}")
        raise Exception('Failed to delete item from DynamoDB') from e
