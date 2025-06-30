import time
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from iou_app.iou import ddb


class TestDynamoDBResourceAndTables:
    @patch('iou_app.iou.ddb.boto3.resource')
    def test_get_dynamodb_resource(self, mock_boto3_resource):
        mock_resource = Mock()
        mock_boto3_resource.return_value = mock_resource

        result = ddb.get_dynamodb_resource()

        mock_boto3_resource.assert_called_once_with('dynamodb', region_name=ddb.AWS_DEFAULT_REGION)
        assert result == mock_resource

    @patch('iou_app.iou.ddb.get_dynamodb_resource')
    def test_get_table(self, mock_get_dynamodb_resource):
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_get_dynamodb_resource.return_value = mock_dynamodb

        result = ddb.get_table()

        mock_dynamodb.Table.assert_called_once_with(ddb.DDB_DATA_TABLE_NAME)
        assert result == mock_table

    @patch('iou_app.iou.ddb.get_dynamodb_resource')
    def test_get_users_table(self, mock_get_dynamodb_resource):
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_get_dynamodb_resource.return_value = mock_dynamodb

        result = ddb.get_users_table()

        mock_dynamodb.Table.assert_called_once_with(ddb.DDB_USERS_TABLE_NAME)
        assert result == mock_table


class TestUserOperations:
    def test_get_all_users_success(self):
        mock_table = Mock()
        mock_table.scan.return_value = {'Items': [{'username': 'alice'}, {'username': 'bob'}]}

        result = ddb.get_all_users(mock_table)

        assert len(result) == 2
        assert result[0]['username'] == 'alice'
        assert result[1]['username'] == 'bob'

    def test_get_all_users_error(self):
        mock_table = Mock()
        mock_table.scan.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='Scan'
        )

        with pytest.raises(Exception, match='Failed to retrieve users from DynamoDB'):
            ddb.get_all_users(mock_table)

    def test_get_user_by_username_cache_hit(self):
        # Setup cache with user data
        current_time = time.time()
        user_data = {'username': 'alice', 'conversation_id': '123'}
        ddb.USER_CACHE['alice'] = (user_data, current_time + 3600)

        mock_table = Mock()

        result = ddb.get_user_by_username('alice', mock_table)

        assert result == user_data
        # Table should not be called due to cache hit
        mock_table.get_item.assert_not_called()

    def test_get_user_by_username_cache_miss(self):
        # Clear cache
        ddb.USER_CACHE.clear()

        mock_table = Mock()
        user_data = {'username': 'alice', 'conversation_id': '123'}
        mock_table.get_item.return_value = {'Item': user_data}

        result = ddb.get_user_by_username('alice', mock_table)

        assert result == user_data
        mock_table.get_item.assert_called_once_with(Key={'username': 'alice'})
        # Should be cached now
        assert 'alice' in ddb.USER_CACHE

    def test_get_user_by_username_cache_expired(self):
        # Setup cache with expired data
        current_time = time.time()
        user_data = {'username': 'alice', 'conversation_id': '123'}
        ddb.USER_CACHE['alice'] = (user_data, current_time - 1)  # Expired

        mock_table = Mock()
        updated_user_data = {'username': 'alice', 'conversation_id': '456'}
        mock_table.get_item.return_value = {'Item': updated_user_data}

        result = ddb.get_user_by_username('alice', mock_table)

        assert result == updated_user_data
        mock_table.get_item.assert_called_once_with(Key={'username': 'alice'})

    def test_get_user_by_username_not_found(self):
        ddb.USER_CACHE.clear()

        mock_table = Mock()
        mock_table.get_item.return_value = {}

        result = ddb.get_user_by_username('nonexistent', mock_table)

        assert result is None

    def test_get_user_by_username_error(self):
        ddb.USER_CACHE.clear()

        mock_table = Mock()
        mock_table.get_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='GetItem'
        )

        with pytest.raises(Exception, match='Failed to retrieve user from DynamoDB'):
            ddb.get_user_by_username('alice', mock_table)

    def test_create_user_success(self):
        mock_table = Mock()
        user_data = {'username': 'alice', 'conversation_id': '123'}

        result = ddb.create_user(user_data, mock_table)

        assert result == user_data
        mock_table.put_item.assert_called_once_with(Item=user_data)
        # Should be cached
        assert 'alice' in ddb.USER_CACHE

    def test_create_user_error(self):
        mock_table = Mock()
        mock_table.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='PutItem'
        )

        user_data = {'username': 'alice', 'conversation_id': '123'}

        with pytest.raises(Exception, match='Failed to create user in DynamoDB'):
            ddb.create_user(user_data, mock_table)

    def test_update_user_success(self):
        mock_table = Mock()
        update_data = {'conversation_id': '456'}
        updated_user = {'username': 'alice', 'conversation_id': '456'}

        mock_table.update_item.return_value = {'Attributes': updated_user}

        result = ddb.update_user('alice', update_data, mock_table)

        assert result == updated_user
        mock_table.update_item.assert_called_once()
        # Should be cached
        assert 'alice' in ddb.USER_CACHE

    def test_update_user_error(self):
        mock_table = Mock()
        mock_table.update_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='UpdateItem'
        )

        update_data = {'conversation_id': '456'}

        with pytest.raises(Exception, match='Failed to update user in DynamoDB'):
            ddb.update_user('alice', update_data, mock_table)


class TestCacheManagement:
    def test_invalidate_user_cache(self):
        # Setup cache
        ddb.USER_CACHE['alice'] = ({'username': 'alice'}, time.time() + 3600)
        ddb.USER_CACHE['bob'] = ({'username': 'bob'}, time.time() + 3600)

        ddb.invalidate_user_cache('alice')

        assert 'alice' not in ddb.USER_CACHE
        assert 'bob' in ddb.USER_CACHE

    def test_invalidate_user_cache_nonexistent(self):
        # Should not raise error for non-existent user
        ddb.invalidate_user_cache('nonexistent')

    def test_clear_user_cache(self):
        # Setup cache
        ddb.USER_CACHE['alice'] = ({'username': 'alice'}, time.time() + 3600)
        ddb.USER_CACHE['bob'] = ({'username': 'bob'}, time.time() + 3600)

        ddb.clear_user_cache()

        assert len(ddb.USER_CACHE) == 0

    def test_clear_entries_cache(self):
        # Setup cache
        ddb.ENTRIES_CACHE['all_entries'] = ([{'id': '1'}], time.time() + 3600)

        ddb.clear_entries_cache()

        assert len(ddb.ENTRIES_CACHE) == 0


class TestEntryOperations:
    def test_write_item_to_dynamodb_success(self):
        mock_table = Mock()
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        item = {
            'conversation_id': '1',
            'sender': 'alice',
            'recipient': 'bob',
            'amount': '10.50',
            'description': 'Coffee',
            'datetime': '2023-01-01 10:00:00'
        }

        mock_uuid = Mock()
        mock_uuid.__str__ = Mock(return_value='test-uuid')
        with patch('iou_app.iou.ddb.uuid.uuid4', return_value=mock_uuid):
            with patch('iou_app.iou.ddb.datetime') as mock_datetime:
                mock_datetime.datetime.now.return_value.strftime.return_value = '2023-01-01 10:00:00'

                result = ddb.write_item_to_dynamodb(item, mock_table)

                # Function returns DynamoDB response, not the modified item
                assert result == {'ResponseMetadata': {'HTTPStatusCode': 200}}
                mock_table.put_item.assert_called_once()

                # Verify the item was modified correctly before being sent to DynamoDB
                put_call_args = mock_table.put_item.call_args
                put_item = put_call_args[1]['Item']  # Get the Item argument
                assert put_item['id'] == 'test-uuid'
                assert put_item['deleted'] == 'False'

    def test_write_item_to_dynamodb_error(self):
        mock_table = Mock()
        mock_table.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='PutItem'
        )

        item = {'conversation_id': '1', 'sender': 'alice', 'datetime': '2023-01-01 10:00:00'}

        with pytest.raises(Exception, match='Failed to write item to DynamoDB'):
            ddb.write_item_to_dynamodb(item, mock_table)

    def test_get_entries_cache_hit(self):
        # Setup cache
        entries_data = [{'id': '1', 'sender': 'alice'}]
        ddb.ENTRIES_CACHE['all_entries'] = (entries_data, time.time() + 3600)

        mock_table = Mock()

        result = ddb.get_entries(mock_table)

        assert result == entries_data
        mock_table.scan.assert_not_called()

    def test_get_entries_cache_miss(self):
        # Clear cache
        ddb.ENTRIES_CACHE.clear()

        mock_table = Mock()
        entries_data = [{'id': '1', 'sender': 'alice'}]
        mock_table.scan.return_value = {'Items': entries_data}

        result = ddb.get_entries(mock_table)

        assert result == entries_data
        mock_table.scan.assert_called_once()
        assert 'all_entries' in ddb.ENTRIES_CACHE

    def test_get_entries_basic_scan(self):
        ddb.ENTRIES_CACHE.clear()

        mock_table = Mock()

        # Mock single scan response with multiple items
        response = {
            'Items': [{'id': '1', 'deleted': 'False'}, {'id': '2', 'deleted': 'False'}]
        }

        mock_table.scan.return_value = response

        result = ddb.get_entries(mock_table)

        assert len(result) == 2
        assert result[0]['id'] == '1'
        assert result[1]['id'] == '2'
        assert mock_table.scan.call_count == 1

    def test_get_entries_error(self):
        ddb.ENTRIES_CACHE.clear()

        mock_table = Mock()
        mock_table.scan.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='Scan'
        )

        with pytest.raises(Exception, match='Failed to retrieve entries from DynamoDB'):
            ddb.get_entries(mock_table)

    def test_get_entry_by_id_success(self):
        mock_table = Mock()
        entry_data = {'id': 'test-id', 'sender': 'alice'}
        mock_table.scan.return_value = {'Items': [entry_data]}

        result = ddb.get_entry_by_id('test-id', mock_table)

        assert result == entry_data
        mock_table.scan.assert_called_once()

    def test_get_entry_by_id_not_found(self):
        mock_table = Mock()
        mock_table.scan.return_value = {'Items': []}

        result = ddb.get_entry_by_id('nonexistent', mock_table)

        assert result is None

    def test_get_entry_by_id_error(self):
        mock_table = Mock()
        mock_table.scan.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='Scan'
        )

        with pytest.raises(Exception, match='Failed to retrieve entry from DynamoDB'):
            ddb.get_entry_by_id('test-id', mock_table)

    def test_update_item_success(self):
        mock_table = Mock()
        scan_response = {'Items': [{'id': 'test-id', 'datetime': '2023-01-01 10:00:00'}]}
        updated_item = {'Attributes': {'id': 'test-id', 'amount': '20.00'}}
        mock_table.scan.return_value = scan_response
        mock_table.update_item.return_value = updated_item

        result = ddb.update_item(
            'test-id',
            'SET amount = :amount',
            {':amount': '20.00'},
            mock_table
        )

        assert result == updated_item
        mock_table.scan.assert_called_once()
        mock_table.update_item.assert_called_once()

    def test_update_item_error(self):
        mock_table = Mock()
        mock_table.scan.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='Scan'
        )

        with pytest.raises(Exception, match='Failed to update item in DynamoDB'):
            ddb.update_item('test-id', 'SET amount = :amount', {':amount': '20.00'}, mock_table)

    def test_soft_delete_item_success(self):
        mock_table = Mock()
        scan_response = {'Items': [{'id': 'test-id', 'datetime': '2023-01-01 10:00:00'}]}
        updated_item = {'Attributes': {'id': 'test-id', 'deleted': True}}
        mock_table.scan.return_value = scan_response
        mock_table.update_item.return_value = updated_item

        with patch('iou_app.iou.ddb.datetime') as mock_datetime:
            mock_datetime.datetime.now.return_value.strftime.return_value = '2023-01-01 10:00:00'

            result = ddb.soft_delete_item('test-id', mock_table)

            assert result == updated_item
            mock_table.scan.assert_called_once()
            mock_table.update_item.assert_called_once()

    def test_soft_delete_item_error(self):
        mock_table = Mock()
        mock_table.scan.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='Scan'
        )

        with pytest.raises(Exception, match='Failed to soft delete item in DynamoDB'):
            ddb.soft_delete_item('test-id', mock_table)

    def test_delete_item_success(self):
        mock_table = Mock()
        scan_response = {'Items': [{'id': 'test-id', 'datetime': '2023-01-01 10:00:00'}]}
        delete_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        mock_table.scan.return_value = scan_response
        mock_table.delete_item.return_value = delete_response

        result = ddb.delete_item('test-id', mock_table)

        assert result == delete_response
        mock_table.scan.assert_called_once()
        mock_table.delete_item.assert_called_once()

    def test_delete_item_error(self):
        mock_table = Mock()
        mock_table.scan.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceException', 'Message': 'Test error'}},
            operation_name='Scan'
        )

        with pytest.raises(Exception, match='Failed to delete item from DynamoDB'):
            ddb.delete_item('test-id', mock_table)


@pytest.mark.parametrize('ttl,should_expire', [
    (3600, False),  # 1 hour, should not expire
    (-1, True),     # Expired
    (1, False),     # 1 second, should not expire immediately
])
def test_user_cache_expiry_parameterized(ttl, should_expire):
    ddb.USER_CACHE.clear()

    current_time = time.time()
    user_data = {'username': 'alice', 'conversation_id': '123'}
    ddb.USER_CACHE['alice'] = (user_data, current_time + ttl)

    mock_table = Mock()
    new_user_data = {'username': 'alice', 'conversation_id': '456'}
    mock_table.get_item.return_value = {'Item': new_user_data}

    result = ddb.get_user_by_username('alice', mock_table, ttl=3600)

    if should_expire:
        assert result == new_user_data
        mock_table.get_item.assert_called_once()
    else:
        assert result == user_data
        mock_table.get_item.assert_not_called()


@pytest.mark.parametrize('entries_data,expected_items', [
    ([{'id': '1', 'deleted': 'False'}], [{'id': '1', 'deleted': 'False'}]),  # Normal case
    ([], []),  # Empty case
])
def test_get_entries_with_different_data_parameterized(entries_data, expected_items):
    ddb.ENTRIES_CACHE.clear()

    mock_table = Mock()
    mock_table.scan.return_value = {'Items': entries_data}

    result = ddb.get_entries(mock_table)

    assert result == expected_items
    mock_table.scan.assert_called_once()
