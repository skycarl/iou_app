import pytest
from app import utils


compute_iou_status_testdata = [
    ([('Alice', 'Bob', 20.)], [('Bob', 'Alice', 10.)], {'user1': 'Alice', 'user2': 'Bob', 'amount': 10.}),
    ([('Alice', 'Bob', 10.)], [('Bob', 'Alice', 10.)], {'user1': 'Alice', 'user2': 'Bob', 'amount': 0.}),
    ([('Alice', 'Bob', 20.), ('Alice', 'Bob', 20.)],
     [('Bob', 'Alice', 10.), ('Bob', 'Alice', 10.)],
     {'user1': 'Alice', 'user2': 'Bob', 'amount': 20.}),
    ([('Alice', 'Bob', 5.)], [('Bob', 'Alice', 10.)], {'user1': 'Bob', 'user2': 'Alice', 'amount': 5.}),
]

@pytest.mark.parametrize('q1, q2, expected', compute_iou_status_testdata)
def test_compute_iou_status(q1, q2, expected):
    assert utils.compute_iou_status(q1, q2) == expected
