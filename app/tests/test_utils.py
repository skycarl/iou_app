import pytest

from app.iou.schema import EntrySchema
from app.iou.utils import compute_iou_status


class TestComputeIOUStatus:
    def test_compute_iou_status_user1_owes_more(self):
        # User1 (alice) owes more to user2 (bob)
        query1 = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=20.0),
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=10.0)
        ]
        query2 = [
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=5.0)
        ]

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'alice'
        assert result['user2'] == 'bob'
        assert result['amount'] == 25.0  # 30 - 5

    def test_compute_iou_status_user2_owes_more(self):
        # User2 (bob) owes more to user1 (alice)
        query1 = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=5.0)
        ]
        query2 = [
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=20.0),
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=10.0)
        ]

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'bob'
        assert result['user2'] == 'alice'
        assert result['amount'] == 25.0  # 30 - 5

    def test_compute_iou_status_equal_amounts(self):
        # Both users owe equal amounts
        query1 = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=15.0),
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=10.0)
        ]
        query2 = [
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=25.0)
        ]

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'alice'
        assert result['user2'] == 'bob'
        assert result['amount'] == 0.0

    def test_compute_iou_status_single_entries(self):
        # Single entry for each user
        query1 = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=100.0)
        ]
        query2 = [
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=50.0)
        ]

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'alice'
        assert result['user2'] == 'bob'
        assert result['amount'] == 50.0

    def test_compute_iou_status_empty_query1(self):
        # User1 has no entries, user2 owes
        query1 = []
        query2 = [
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=30.0)
        ]

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'bob'
        assert result['user2'] == 'alice'
        assert result['amount'] == 30.0

    def test_compute_iou_status_empty_query2(self):
        # User2 has no entries, user1 owes
        query1 = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=40.0)
        ]
        query2 = []

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'alice'
        assert result['user2'] == 'bob'
        assert result['amount'] == 40.0

    def test_compute_iou_status_both_empty_queries(self):
        # Both queries are empty - should raise ValueError
        query1 = []
        query2 = []

        with pytest.raises(ValueError, match='IOU status not found'):
            compute_iou_status(query1, query2)

    def test_compute_iou_status_decimal_amounts(self):
        # Test with decimal amounts
        query1 = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=12.75),
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=7.25)
        ]
        query2 = [
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=5.50)
        ]

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'alice'
        assert result['user2'] == 'bob'
        assert result['amount'] == 14.5  # 20.0 - 5.5

    def test_compute_iou_status_large_numbers(self):
        # Test with large amounts
        query1 = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=1000.0)
        ]
        query2 = [
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=750.0)
        ]

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'alice'
        assert result['user2'] == 'bob'
        assert result['amount'] == 250.0

    def test_compute_iou_status_many_entries(self):
        # Test with many entries
        query1 = [
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=10.0),
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=15.0),
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=20.0),
            EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=5.0)
        ]
        query2 = [
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=25.0),
            EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=10.0)
        ]

        result = compute_iou_status(query1, query2)

        assert result['user1'] == 'alice'
        assert result['user2'] == 'bob'
        assert result['amount'] == 15.0  # 50 - 35


@pytest.mark.parametrize('alice_amounts,bob_amounts,expected_owing_user,expected_amount', [
    # Alice owes more
    ([20.0, 10.0], [5.0], 'alice', 25.0),
    # Bob owes more
    ([5.0], [20.0, 10.0], 'bob', 25.0),
    # Equal amounts
    ([15.0], [15.0], 'alice', 0.0),
    # Alice owes, Bob has no entries
    ([30.0], [], 'alice', 30.0),
    # Bob owes, Alice has no entries
    ([], [40.0], 'bob', 40.0),
    # Small decimal differences
    ([12.25], [12.50], 'bob', 0.25),
    # Large amounts
    ([1000.0], [999.99], 'alice', 0.01),
])
def test_compute_iou_status_parameterized(alice_amounts, bob_amounts, expected_owing_user, expected_amount):
    """Parameterized test for various IOU status scenarios."""
    query1 = [
        EntrySchema(conversation_id='1', sender='alice', recipient='bob', amount=amount)
        for amount in alice_amounts
    ] if alice_amounts else []

    query2 = [
        EntrySchema(conversation_id='1', sender='bob', recipient='alice', amount=amount)
        for amount in bob_amounts
    ] if bob_amounts else []

    # Skip the case where both are empty (handled separately)
    if not query1 and not query2:
        pytest.skip('Both queries empty - handled in separate test')

    result = compute_iou_status(query1, query2)

    assert result['user1'] == expected_owing_user
    if expected_owing_user == 'alice':
        assert result['user2'] == 'bob'
    else:
        assert result['user2'] == 'alice'
    assert result['amount'] == pytest.approx(expected_amount, abs=1e-10)


@pytest.mark.parametrize('conversation_id,description', [
    ('12345', 'Test transaction'),
    ('abc', None),
    ('999', 'Multiple items'),
])
def test_compute_iou_status_different_metadata(conversation_id, description):
    """Test that different conversation IDs and descriptions don't affect calculation."""
    query1 = [
        EntrySchema(
            conversation_id=conversation_id,
            sender='alice',
            recipient='bob',
            amount=25.0,
            description=description
        )
    ]
    query2 = [
        EntrySchema(
            conversation_id=conversation_id,
            sender='bob',
            recipient='alice',
            amount=10.0,
            description=description
        )
    ]

    result = compute_iou_status(query1, query2)

    assert result['user1'] == 'alice'
    assert result['user2'] == 'bob'
    assert result['amount'] == 15.0


def test_compute_iou_status_preserves_user_names():
    """Test that user names are preserved correctly in the result."""
    query1 = [
        EntrySchema(conversation_id='1', sender='alice_smith', recipient='bob_jones', amount=50.0)
    ]
    query2 = [
        EntrySchema(conversation_id='1', sender='bob_jones', recipient='alice_smith', amount=30.0)
    ]

    result = compute_iou_status(query1, query2)

    assert result['user1'] == 'alice_smith'
    assert result['user2'] == 'bob_jones'
    assert result['amount'] == 20.0
