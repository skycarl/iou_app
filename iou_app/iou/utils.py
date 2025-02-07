"""Utility functions for the app."""
from typing import List

from loguru import logger

from iou_app.iou.schema import EntrySchema

def compute_iou_status(query1: List[EntrySchema], query2: List[EntrySchema]):
    """Compute the IOU status between two users.

    Parameters
    ----------
    query1 : list
        List of tuples of entries where user1 is the sender
    query2 : list
        List of tuples of entries where user2 is the sender

    Returns
    -------
    iou_status : dict
        Dictionary with keys 'user1', 'user2', and 'iou_status'.
        Interpretation is that `user1` owes `user2` the specified `amount`.
    """

    # Compute the sum of all entries between user1 and user2, negating the amount if user1 is the sender
    user1_sum = sum([entry.amount for entry in query1])
    user2_sum = sum([entry.amount for entry in query2])

    # Compute the IOU status
    if user1_sum > user2_sum:
        iou_status = {'user1': query1[0].sender, 'user2': query1[0].recipient, 'amount': user1_sum - user2_sum}
    elif user2_sum > user1_sum:
        iou_status = {'user1': query2[0].sender, 'user2': query2[0].recipient, 'amount': user2_sum - user1_sum}
    elif user1_sum == user2_sum:
        iou_status = {'user1': query1[0].sender, 'user2': query1[0].recipient, 'amount': 0.}
    else:
        err_msg = f'IOU status not found with query1={query1} and query2={query2}'
        logger.error(err_msg)
        raise ValueError(err_msg)

    return iou_status
