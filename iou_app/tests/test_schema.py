import pytest
from pydantic import ValidationError

from iou_app.iou.schema import AmountException
from iou_app.iou.schema import EntrySchema
from iou_app.iou.schema import IOUMessage
from iou_app.iou.schema import IOUQuery
from iou_app.iou.schema import IOUStatus
from iou_app.iou.schema import SplitResponse
from iou_app.iou.schema import SplitSchema
from iou_app.iou.schema import TransactionEntry
from iou_app.iou.schema import User
from iou_app.iou.schema import UserUpdate
from iou_app.iou.schema import validate_amount_str

@ pytest.mark.parametrize(
    'input_str, expected',
    [
        ('123', 123.0),
        ('1,234.56', 1234.56),
        ('12abc34', AmountException),
        ('-123.45', AmountException),
        ('0', AmountException),
    ],
)
def test_validate_amount_str(input_str, expected):
    if expected is AmountException:
        with pytest.raises(AmountException):
            validate_amount_str(input_str)
    else:
        assert validate_amount_str(input_str) == expected


def test_entryschema_cast_and_amount_validation():
    # conversation_id cast from int to str
    entry = EntrySchema(conversation_id=123, sender='a', recipient='b', amount=1.23)
    assert isinstance(entry.conversation_id, str) and entry.conversation_id == '123'
    # negative amount should raise ValueError
    with pytest.raises(ValueError):
        EntrySchema(conversation_id='1', sender='a', recipient='b', amount=-5)


@ pytest.mark.parametrize(
    'sender, recipient, amt, expected_amt_str',
    [
        ('@alice', '@bob', '45.6', '$45.60'),
        ('alice', 'bob', 30, '$30.00'),
    ],
)
def test_ioumessage_parsing_and_str(sender, recipient, amt, expected_amt_str):
    msg = IOUMessage(conversation_id=1, sender=sender, recipient=recipient, amount=amt, description='Test description')
    assert msg.sender == 'alice' and msg.recipient == 'bob'
    assert isinstance(msg.amount, float)
    assert msg.amount_str == expected_amt_str


def test_ioumessage_invalid_amount():
    with pytest.raises(ValidationError):
        IOUMessage(conversation_id=1, sender='a', recipient='b', amount=0, description='Invalid amount test')
    with pytest.raises(ValidationError):
        IOUMessage(conversation_id=1, sender='a', recipient='b', amount=[1,2], description='Invalid amount test')


@ pytest.mark.parametrize(
    'user1, user2, expected1, expected2',
    [
        ('@u1', '@u2', 'u1', 'u2'),
        ('u1', 'u2', 'u1', 'u2'),
    ],
)
def test_iouquery_strip(user1, user2, expected1, expected2):
    q = IOUQuery(conversation_id=1, user1=user1, user2=user2)
    assert q.user1 == expected1 and q.user2 == expected2


@ pytest.mark.parametrize(
    'amt, expected',
    [(1.234, 1.23), (1.235, 1.24)],
)
def test_ioustatus_round(amt, expected):
    st = IOUStatus(owing_user='a', owed_user='b', amount=amt)
    assert st.amount == expected


def test_splitschema_parsing_and_str():
    split = SplitSchema(
        conversation_id='1',
        payer='@p',
        amount='100.5',
        participants=['a', 'b'],
        description='desc',
    )
    assert split.payer == 'p'
    assert split.amount == 100.5
    assert split.amount_str == '$100.50'


def test_splitresponse_round_and_str():
    resp = SplitResponse(
        message='ok',
        amount=2.345,
        split_per_user=1.234,
        participants=['a', 'b'],
    )
    assert resp.amount == 2.35
    assert resp.split_per_user == 1.23
    assert resp.amount_str == '$2.35'
    assert resp.split_per_user_str == '$1.23'


def test_transactionentry_fields():
    te = TransactionEntry(
        conversation_id='c',
        sender='s',
        recipient='r',
        amount=123.4,
        timestamp='2021-01-02T03:04:05',
    )
    assert te.amount_str == '$123.40'
    assert te.formatted_date == '2021-01-02'
    # no timestamp
    te2 = TransactionEntry(
        conversation_id='c',
        sender='s',
        recipient='r',
        amount=1,
    )
    assert te2.formatted_date == ''
    # invalid timestamp
    te3 = TransactionEntry(
        conversation_id='c',
        sender='s',
        recipient='r',
        amount=1,
        timestamp='not-date',
    )
    assert te3.formatted_date == 'not-date'


def test_user_models_defaults():
    u = User(username='u')
    assert u.conversation_id is None
    uu = UserUpdate(conversation_id='1234')
    assert uu.conversation_id == '1234'
