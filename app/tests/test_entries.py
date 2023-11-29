import os
from unittest.mock import Mock, patch
from dotenv import load_dotenv

from app.main import app
from app.core.db.session import Base
from app.core.db.mock_session import engine, test_client

load_dotenv(".env")

# It drops everything from the db and then recreate each time tests runs
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = test_client()
X_TOKEN = os.environ["X_TOKEN"]
HEADERS = {"X-Token": X_TOKEN}
ENDPOINT = "/api/entries"
LAST_RECORD_ID = 1
PAYLOAD = {
    "conversation_id": 1,
    "sender": "alice",
    "recipient": "bob",
    "amount": 42,
    "description": "Stuff",
}


def test_invalid_x_token():
    """
    Test if it the endpoint is invalid without the token
    """
    response = client.get(ENDPOINT, params=PAYLOAD)
    assert response.status_code == 422


def test_add_entry():

    """
    Tests if the entries are being added to the database
    """

    response = client.post(ENDPOINT, json=PAYLOAD, headers=HEADERS)
    data = response.json()

    # validates if the request was successfull
    assert response.status_code == 201

    print(data)

    # validates the saved record
    assert ("conversation_id" in data) and ("sender" in data)


def test_get_entry():

    """
    Tests if the entries get request is successfull
    """

    response = client.get(ENDPOINT, headers=HEADERS)

    # validates if the request was successfull
    assert response.status_code == 200


def test_add_invalid_entry():

    """
    Tests if it validates the inavlid payload
    """

    invalid_payload = PAYLOAD.copy()
    invalid_payload.pop("conversation_id", None)

    response = client.post(ENDPOINT, json=invalid_payload, headers=HEADERS)

    # validates if the request was invalid because of inappropriate data
    assert response.status_code == 422


def test_update_entry():

    """
    Tests if the entry is being updated
    """

    updated_payload = PAYLOAD.copy()
    updated_payload["description"] = "Breakfast"
    response = client.put(
        f"{ENDPOINT}/{LAST_RECORD_ID}", json=updated_payload, headers=HEADERS
    )

    # validates if the request was successfull
    assert response.status_code == 201


def test_invalid_update_entry():

    """
    Tests if it doesn't update with invalid id
    """

    updated_payload = PAYLOAD.copy()
    updated_payload["description"] = "something"
    response = client.put(f"{ENDPOINT}/12345", json=updated_payload, headers=HEADERS)

    # validates if the it threw an error on invalid id
    assert response.status_code == 404


def test_delete_entry():

    """
    Tests if the entry is being deleted
    """

    response = client.delete(f"{ENDPOINT}/{LAST_RECORD_ID}", headers=HEADERS)

    # validates if the request was successfull
    assert response.status_code == 204


def test_invalid_delete_entry():

    """
    Tests if it doesn't delete with invalid id
    """

    response = client.delete(f"{ENDPOINT}/12345", headers=HEADERS)

    # validates if the it threw an error on invalid id
    assert response.status_code == 404
