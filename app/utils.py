"""Utility functions for the app."""

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
        Dictionary with keys 'user1', 'user2', and 'iou_status'. Interpretation is that `user1` owes `user2` the specified `amount`.
    """

    # Compute the sum of all entries between user1 and user2, negating the amount if user1 is the sender
    user1_sum = sum([entry[2] for entry in query1])
    user2_sum = sum([entry[2] for entry in query2])

    # Compute the IOU status
    if user1_sum > user2_sum:
        iou_status = {"user1": query1[0][0], "user2": query1[0][1], "amount": user1_sum - user2_sum}
    elif user2_sum > user1_sum:
        iou_status = {"user1": query2[0][0], "user2": query2[0][1], "amount": user2_sum - user1_sum}
    else:
        iou_status = {"user1": query1[0][0], "user2": query1[0][1], "amount": 0}

    return iou_status
