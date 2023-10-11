# IOU app

A simple app to keep track of IOUs between people.

## Use case

Anna and Joey are friends. Anna paid for something (dinner, movie tickets, etc) for Joey. Rather than sending Joey's half of the bill to Anna through Zelle/Venmo/etc, Joey can just "send" Anna money through the app. The app will keep track of who owes who how much, and anyone can query the app to see who should pay for the next thing so that people stay mostly even. 

## Run

How to run locally

```bash
uvicorn app.main:app --reload
```

within container

```bash
python -m uvicorn app.main:app --reload
```

## MVP features

- [x] Create IOU
- [x] List IOUs
- [x] Delete IOU
- [x] Find participant with max IOU
- [x] Add recipient to IOU
- [x] Add conversation ID
- [x] Change IOU status to be for each pair of participants, e.g., who owes who how much
- [x] Update response when user isn't found in a query
- [x] Ensure IOUs are positive
- [ ] Switch to postgreSQL database rather than sqlite
 
## Feature ideas

- [ ] Recurring IOU
- [ ] Support multiple chats (e.g. group by chat ID)
- [ ] Split bill between everyone (or specified users in chat)
- [ ] Group participants (e.g., by household)
- [ ] Settle IOUs (e.g., figure out who owes who how much and add negative amount to transactions)
- [ ] List all transactions
- [ ] Request an IOU (have someone confirm? or nah?)
- [ ] When validating users, suggest a close match, e.g., "did you mean XYZ?"
- [ ] Validate that users are a member of the conversation
    - [ ] First stage is to have this in the bot (since that has awareness of the group text). Second level of maturity is to handle it in the backend 
- [ ] Clean up images -- can probably just use a single image for both containers to reduce CI demands