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

    # Handle empty queries
    if not query1 and not query2:
        err_msg = f'IOU status not found with query1={query1} and query2={query2}'
        logger.error(err_msg)
        raise ValueError(err_msg)

    # Get user names from available queries
    if query1:
        user1_name = query1[0].sender
        user2_name = query1[0].recipient
    else:
        user1_name = query2[0].recipient  # Reverse since this is user2's query
        user2_name = query2[0].sender

    # Compute the IOU status
    if user1_sum > user2_sum:
        iou_status = {'user1': user1_name, 'user2': user2_name, 'amount': user1_sum - user2_sum}
    elif user2_sum > user1_sum:
        # When user2 owes more, the owing user should be from query2 if available
        owing_user = query2[0].sender if query2 else user2_name
        owed_user = query2[0].recipient if query2 else user1_name
        iou_status = {'user1': owing_user, 'user2': owed_user, 'amount': user2_sum - user1_sum}
    elif user1_sum == user2_sum:
        iou_status = {'user1': user1_name, 'user2': user2_name, 'amount': 0.}
    else:
        err_msg = f'IOU status not found with query1={query1} and query2={query2}'
        logger.error(err_msg)
        raise ValueError(err_msg)

    return iou_status
