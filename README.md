# IOU app

A simple app to keep track of IOUs between people.

## Use case

Anna and Joey are friends. Anna paid for something (dinner, movie tickets, etc) for Joey. Rather than sending Joey's half of the bill to Anna through Zelle/Venmo/etc, Joey can just "send" Anna money through the app. The app will keep track of who owes who how much, and anyone can query the app to see who should pay for the next thing so that people stay mostly even. 

## Run

How to run locally

```bash
uvicorn app.main:app --reload
```

## MVP features

- [x] Create IOU
- [x] List IOUs
- [x] Delete IOU (query for latest 5 entries with IDs?)
- [x] Find participant with max IOU

## Feature ideas

- [ ] Recurring IOU
- [ ] Support multiple chats (e.g. group by chat ID)
- [ ] Split bill between everyone
- [ ] Group participants (e.g., by household)
- [ ] Settle IOUs (e.g., figure out who owes who how much)