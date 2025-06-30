from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from iou_app.iou.schema import EntrySchema
from iou_app.iou.schema import IOUStatus
from iou_app.iou.schema import SplitSchema
from iou_app.iou.schema import User
from iou_app.iou.schema import UserUpdate
from iou_app.iou.views import get_version


# Mock data
MOCK_ENTRIES = [
    {
        'conversation_id': '1',
        'sender': 'alice',
        'recipient': 'bob',
        'amount': '10.50',
        'description': 'Coffee',
        'datetime': '2023-01-01 10:00:00',
        'deleted': 'False',
        'id': 'entry1'
    },
    {
        'conversation_id': '1',
        'sender': 'bob',
        'recipient': 'alice',
        'amount': '5.25',
        'description': 'Lunch',
        'datetime': '2023-01-02 12:00:00',
        'deleted': 'False',
        'id': 'entry2'
    }
]

MOCK_USER = {
    'username': 'alice',
    'conversation_id': '12345'
}


class TestGetVersion:
    @patch('builtins.open', mock_open(read_data='''
[tool]
[tool.poetry]
version = "1.2.3"
'''))
    def test_get_version_function(self):
        with patch('iou_app.iou.views.toml.load') as mock_load:
            mock_load.return_value = {'tool': {'poetry': {'version': '1.2.3'}}}
            version = get_version()
            assert version == '1.2.3'

    @patch('iou_app.iou.views.get_version')
    @pytest.mark.asyncio
    async def test_get_version_endpoint(self, mock_get_version):
        mock_get_version.return_value = '1.2.3'
        from iou_app.iou.views import get_version_endpoint

        result = await get_version_endpoint()
        assert result == {'version': '1.2.3'}


class TestGetEntries:
    @patch('iou_app.iou.views.ddb_get_entries')
    @pytest.mark.asyncio
    async def test_get_entries_no_filters(self, mock_ddb_get_entries):
        from iou_app.iou.views import get_entries

        mock_ddb_get_entries.return_value = MOCK_ENTRIES
        mock_table = Mock()

        result = await get_entries(table=mock_table)

        assert len(result) == 2
        assert result[0].sender == 'alice'
        assert result[0].recipient == 'bob'
        assert result[0].amount == 10.50

    @patch('iou_app.iou.views.ddb_get_entries')
    @pytest.mark.asyncio
    async def test_get_entries_with_user1_filter(self, mock_ddb_get_entries):
        from iou_app.iou.views import get_entries

        mock_ddb_get_entries.return_value = MOCK_ENTRIES
        mock_table = Mock()

        result = await get_entries(user1='alice', table=mock_table)

        assert len(result) == 2  # Alice is involved in both transactions

    @patch('iou_app.iou.views.ddb_get_entries')
    @pytest.mark.asyncio
    async def test_get_entries_with_both_users_filter(self, mock_ddb_get_entries):
        from iou_app.iou.views import get_entries

        mock_ddb_get_entries.return_value = MOCK_ENTRIES
        mock_table = Mock()

        result = await get_entries(user1='alice', user2='bob', table=mock_table)

        assert len(result) == 2  # Both entries are between alice and bob

    @patch('iou_app.iou.views.ddb_get_entries')
    @pytest.mark.asyncio
    async def test_get_entries_no_data(self, mock_ddb_get_entries):
        from iou_app.iou.views import get_entries

        mock_ddb_get_entries.return_value = []
        mock_table = Mock()

        result = await get_entries(table=mock_table)

        assert result == []

    @patch('iou_app.iou.views.ddb_get_entries')
    @pytest.mark.asyncio
    async def test_get_entries_database_error(self, mock_ddb_get_entries):
        from iou_app.iou.views import get_entries

        mock_ddb_get_entries.side_effect = Exception('Database error')
        mock_table = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await get_entries(table=mock_table)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == 'Internal server error'


class TestAddEntry:
    @patch('iou_app.iou.views.write_item_to_dynamodb')
    @pytest.mark.asyncio
    async def test_add_entry_success(self, mock_write_item):
        from iou_app.iou.views import add_entry

        mock_write_item.return_value = {'id': 'new_entry_id'}
        mock_table = Mock()

        entry_data = EntrySchema(
            conversation_id='1',
            sender='alice',
            recipient='bob',
            amount=15.75,
            description='Test entry'
        )

        result = await add_entry(entry_data, mock_table)

        assert result.sender == 'alice'
        assert result.recipient == 'bob'
        assert result.amount == 15.75
        assert result.timestamp is not None

        mock_write_item.assert_called_once()

    @patch('iou_app.iou.views.write_item_to_dynamodb')
    @pytest.mark.asyncio
    async def test_add_entry_database_error(self, mock_write_item):
        from iou_app.iou.views import add_entry

        mock_write_item.side_effect = Exception('Database error')
        mock_table = Mock()

        entry_data = EntrySchema(
            conversation_id='1',
            sender='alice',
            recipient='bob',
            amount=15.75
        )

        with pytest.raises(HTTPException) as exc_info:
            await add_entry(entry_data, mock_table)

        assert exc_info.value.status_code == 500


class TestIOUStatus:
    @patch('iou_app.iou.views.get_entries')
    @pytest.mark.asyncio
    async def test_iou_status_user1_owes_more(self, mock_get_entries):
        from iou_app.iou.views import read_iou_status

        # Alice owes Bob more
        entries = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=20.0),
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=5.0)
        ]
        mock_get_entries.return_value = entries
        mock_table = Mock()

        result = await read_iou_status('alice', 'bob', mock_table)

        assert result.owing_user == 'alice'
        assert result.owed_user == 'bob'
        assert result.amount == 15.0

    @patch('iou_app.iou.views.get_entries')
    @pytest.mark.asyncio
    async def test_iou_status_user2_owes_more(self, mock_get_entries):
        from iou_app.iou.views import read_iou_status

        # Bob owes Alice more
        entries = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=5.0),
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=20.0)
        ]
        mock_get_entries.return_value = entries
        mock_table = Mock()

        result = await read_iou_status('alice', 'bob', mock_table)

        assert result.owing_user == 'bob'
        assert result.owed_user == 'alice'
        assert result.amount == 15.0

    @patch('iou_app.iou.views.get_entries')
    @pytest.mark.asyncio
    async def test_iou_status_even(self, mock_get_entries):
        from iou_app.iou.views import read_iou_status

        # Even amounts
        entries = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=10.0),
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=10.0)
        ]
        mock_get_entries.return_value = entries
        mock_table = Mock()

        result = await read_iou_status('alice', 'bob', mock_table)

        assert result.owing_user == 'alice'
        assert result.owed_user == 'bob'
        assert result.amount == 0.0


class TestSplitAmount:
    @patch('iou_app.iou.views.add_entry')
    @pytest.mark.asyncio
    async def test_split_amount_success(self, mock_add_entry):
        from iou_app.iou.views import split_amount

        mock_add_entry.return_value = None
        mock_table = Mock()

        split_data = SplitSchema(
            conversation_id='1',
            payer='alice',
            amount=30.0,
            participants=['alice', 'bob', 'charlie'],
            description='Dinner'
        )

        result = await split_amount(split_data, mock_table)

        assert result['message'] == 'Split successful'
        assert result['amount'] == 30.0
        assert result['split_per_user'] == 10.0
        assert len(result['participants']) == 3

        # Should create 2 entries (payer doesn't owe themselves)
        assert mock_add_entry.call_count == 2

    @pytest.mark.asyncio
    async def test_split_amount_insufficient_participants(self):
        from iou_app.iou.views import split_amount

        mock_table = Mock()

        split_data = SplitSchema(
            conversation_id='1',
            payer='alice',
            amount=30.0,
            participants=['alice'],  # Only one participant
            description='Dinner'
        )

        result = await split_amount(split_data, mock_table)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400


class TestUserEndpoints:
    @patch('iou_app.iou.views.get_user_by_username')
    @patch('iou_app.iou.views.create_user')
    @pytest.mark.asyncio
    async def test_add_user_success(self, mock_create_user, mock_get_user):
        from iou_app.iou.views import add_user

        mock_get_user.return_value = None  # User doesn't exist
        mock_create_user.return_value = MOCK_USER
        mock_table = Mock()

        user_data = User(username='alice', conversation_id='12345')

        result = await add_user(user_data, mock_table)

        assert result.username == 'alice'
        assert result.conversation_id == '12345'

    @patch('iou_app.iou.views.get_user_by_username')
    @pytest.mark.asyncio
    async def test_add_user_already_exists(self, mock_get_user):
        from iou_app.iou.views import add_user

        mock_get_user.return_value = MOCK_USER  # User exists
        mock_table = Mock()

        user_data = User(username='alice', conversation_id='12345')

        with pytest.raises(HTTPException) as exc_info:
            await add_user(user_data, mock_table)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == 'User already exists'

    @patch('iou_app.iou.views.get_user_by_username')
    @pytest.mark.asyncio
    async def test_get_user_success(self, mock_get_user):
        from iou_app.iou.views import get_user

        mock_get_user.return_value = MOCK_USER
        mock_table = Mock()

        result = await get_user('alice', mock_table)

        assert result['username'] == 'alice'
        assert result['conversation_id'] == '12345'

    @patch('iou_app.iou.views.get_user_by_username')
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_get_user):
        from iou_app.iou.views import get_user

        mock_get_user.return_value = None
        mock_table = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await get_user('nonexistent', mock_table)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == 'User not found'

    @patch('iou_app.iou.views.get_user_by_username')
    @patch('iou_app.iou.views.update_user')
    @pytest.mark.asyncio
    async def test_update_user_success(self, mock_update_user, mock_get_user):
        from iou_app.iou.views import update_user_endpoint

        mock_get_user.return_value = MOCK_USER
        updated_user = MOCK_USER.copy()
        updated_user['conversation_id'] = '54321'
        mock_update_user.return_value = updated_user
        mock_table = Mock()

        update_data = UserUpdate(conversation_id='54321')

        result = await update_user_endpoint('alice', update_data, mock_table)

        assert result.username == 'alice'
        assert result.conversation_id == '54321'

    @patch('iou_app.iou.views.get_all_users')
    @pytest.mark.asyncio
    async def test_get_users_success(self, mock_get_all_users):
        from iou_app.iou.views import get_users

        mock_get_all_users.return_value = [MOCK_USER]
        mock_table = Mock()

        result = await get_users(mock_table)

        assert len(result) == 1
        assert result[0].username == 'alice'


class TestEntryEndpoints:
    @patch('iou_app.iou.views.get_entry_by_id')
    @patch('iou_app.iou.views.soft_delete_item')
    @pytest.mark.asyncio
    async def test_delete_entry_success(self, mock_soft_delete, mock_get_entry):
        from iou_app.iou.views import delete_entry

        mock_get_entry.return_value = MOCK_ENTRIES[0]
        mock_soft_delete.return_value = None
        mock_table = Mock()

        result = await delete_entry('entry1', mock_table)

        assert result['message'] == 'Entry deleted successfully'
        assert result['id'] == 'entry1'

    @patch('iou_app.iou.views.get_entry_by_id')
    @pytest.mark.asyncio
    async def test_delete_entry_not_found(self, mock_get_entry):
        from iou_app.iou.views import delete_entry

        mock_get_entry.return_value = None
        mock_table = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await delete_entry('nonexistent', mock_table)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == 'Entry not found'

    @patch('iou_app.iou.views.get_entry_by_id')
    @pytest.mark.asyncio
    async def test_get_entry_success(self, mock_get_entry):
        from iou_app.iou.views import get_entry

        mock_get_entry.return_value = MOCK_ENTRIES[0]
        mock_table = Mock()

        result = await get_entry('entry1', mock_table)

        assert result.conversation_id == '1'
        assert result.sender == 'alice'
        assert result.recipient == 'bob'
        assert result.amount == 10.50

    @patch('iou_app.iou.views.get_entry_by_id')
    @pytest.mark.asyncio
    async def test_get_entry_not_found(self, mock_get_entry):
        from iou_app.iou.views import get_entry

        mock_get_entry.return_value = None
        mock_table = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await get_entry('nonexistent', mock_table)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == 'Entry not found'


class TestSettleTransactions:
    @patch('iou_app.iou.views.ddb_get_entries')
    @patch('iou_app.iou.views.read_iou_status')
    @patch('iou_app.iou.views.soft_delete_item')
    @pytest.mark.asyncio
    async def test_settle_transactions_success(self, mock_soft_delete, mock_read_iou_status, mock_ddb_get_entries):
        from iou_app.iou.views import settle_transactions

        mock_ddb_get_entries.return_value = MOCK_ENTRIES
        mock_read_iou_status.return_value = IOUStatus(owing_user='alice', owed_user='bob', amount=5.25)
        mock_soft_delete.return_value = None
        mock_table = Mock()

        result = await settle_transactions('alice', 'bob', mock_table)

        assert 'Successfully settled all transactions' in result['message']
        assert result['transactions_settled'] == 2
        assert result['final_status'].owing_user == 'alice'

    @patch('iou_app.iou.views.ddb_get_entries')
    @pytest.mark.asyncio
    async def test_settle_transactions_no_data(self, mock_ddb_get_entries):
        from iou_app.iou.views import settle_transactions

        mock_ddb_get_entries.return_value = []
        mock_table = Mock()

        result = await settle_transactions('alice', 'bob', mock_table)

        assert result['message'] == 'No transactions found'
        assert result['transactions_settled'] == 0

    @patch('iou_app.iou.views.ddb_get_entries')
    @pytest.mark.asyncio
    async def test_settle_transactions_no_matching_users(self, mock_ddb_get_entries):
        from iou_app.iou.views import settle_transactions

        mock_ddb_get_entries.return_value = MOCK_ENTRIES
        mock_table = Mock()

        result = await settle_transactions('charlie', 'dave', mock_table)

        assert 'No transactions found between charlie and dave' in result['message']
        assert result['transactions_settled'] == 0


@pytest.mark.parametrize('user1,user2,expected_entries', [
    ('alice', None, 2),  # Alice involved in both
    ('bob', None, 2),    # Bob involved in both
    ('alice', 'bob', 2), # Both between alice and bob
    ('charlie', None, 0), # Charlie not involved
    ('alice', 'charlie', 0), # No transactions between alice and charlie
])
@patch('iou_app.iou.views.ddb_get_entries')
@pytest.mark.asyncio
async def test_get_entries_filtering_parameterized(mock_ddb_get_entries, user1, user2, expected_entries):
    from iou_app.iou.views import get_entries

    mock_ddb_get_entries.return_value = MOCK_ENTRIES
    mock_table = Mock()

    result = await get_entries(user1=user1, user2=user2, table=mock_table)

    assert len(result) == expected_entries
