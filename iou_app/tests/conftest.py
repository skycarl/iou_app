from unittest.mock import Mock

import pytest

from iou_app.iou import ddb


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before each test to ensure clean state."""
    ddb.USER_CACHE.clear()
    ddb.ENTRIES_CACHE.clear()
    yield
    # Clean up after test
    ddb.USER_CACHE.clear()
    ddb.ENTRIES_CACHE.clear()


@pytest.fixture
def mock_dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    mock_table = Mock()
    mock_table.table_name = 'test-table'
    return mock_table


@pytest.fixture
def mock_users_table():
    """Create a mock DynamoDB users table for testing."""
    mock_table = Mock()
    mock_table.table_name = 'test-users-table'
    return mock_table


@pytest.fixture
def sample_entry_data():
    """Sample entry data for testing."""
    return {
        'conversation_id': '12345',
        'sender': 'alice',
        'recipient': 'bob',
        'amount': '10.50',
        'description': 'Coffee',
        'datetime': '2023-01-01 10:00:00',
        'deleted': 'False',
        'id': 'test-entry-id'
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        'username': 'alice',
        'conversation_id': '12345'
    }


@pytest.fixture
def sample_entries_list():
    """Sample list of entries for testing."""
    return [
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


@pytest.fixture
def sample_users_list():
    """Sample list of users for testing."""
    return [
        {'username': 'alice', 'conversation_id': '12345'},
        {'username': 'bob', 'conversation_id': '67890'},
        {'username': 'charlie', 'conversation_id': '11111'}
    ]


# Custom markers for different test categories
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line('markers', 'unit: unit tests')
    config.addinivalue_line('markers', 'integration: integration tests')
    config.addinivalue_line('markers', 'slow: slow running tests')
    config.addinivalue_line('markers', 'database: tests that involve database operations')
    config.addinivalue_line('markers', 'cache: tests that involve caching functionality')
