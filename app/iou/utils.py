"""Utility functions for the app."""
import logging

from app.iou.models import EntryModel

logger = logging.getLogger(__name__)

def compute_iou_status(query1, query2):
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
    user1_sum = sum([entry[2] for entry in query1])
    user2_sum = sum([entry[2] for entry in query2])

    # Compute the IOU status
    if user1_sum > user2_sum:
        iou_status = {'user1': query1[0][0], 'user2': query1[0][1], 'amount': user1_sum - user2_sum}
    elif user2_sum > user1_sum:
        iou_status = {'user1': query2[0][0], 'user2': query2[0][1], 'amount': user2_sum - user1_sum}
    elif user1_sum == user2_sum:
        iou_status = {'user1': query1[0][0], 'user2': query1[0][1], 'amount': 0.}
    else:
        err_msg = f'IOU status not found with query1={query1} and query2={query2}'
        logger.error(err_msg)
        raise ValueError(err_msg)

    return iou_status

def query_for_user(db, user1, user2, conversation_id):
    """Query the database for all entries between two users."""

    query = db.query(EntryModel.sender,
                    EntryModel.recipient,
                    EntryModel.amount).filter(
        EntryModel.deleted is False).filter(
        EntryModel.conversation_id == conversation_id).filter(
        EntryModel.sender == user1, EntryModel.recipient == user2).all()

    return query
