import requests

url = 'http://localhost:8000/entries'
entry1 = {
    'conversation_id': 0,
    'sender': 'Alice',
    'recipient': 'Bob',
    'description': 'Dinner',
    'amount': 120.00
}

entry2 = {
    'conversation_id': 0,
    'sender': 'Bob',
    'recipient': 'Alice',
    'description': 'Lunch',
    'amount': 20.00
}

entry3 = {
    'conversation_id': 1,
    'sender': 'Alice',
    'recipient': 'Frank',
    'description': 'Coffee',
    'amount': 5.00
}

entries = [entry1, entry2, entry3]

for entry in entries:
    response = requests.post(url, json=entry)
    print(response.status_code)
