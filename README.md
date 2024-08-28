<h1 align="center">
🍲  IOU App
</h1>

<h2 align="center">
  Simple app for IOU's
</h2>

# Setup

## Step 1

Update **.env.*** file in root directory

```
DATABASE_URL=postgresql+psycopg://postgres:password@db:5432/boiler_plate_db
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=boiler_plate_db
PGADMIN_EMAIL=admin@admin.com
PGADMIN_PASSWORD=admin
X_TOKEN=12345678910
```

## Step 2
```
docker compose up
```

# Use case

A simple app to keep track of IOUs between people.

Anna and Joey are friends. Anna paid for something (dinner, movie tickets, etc) for Joey. Rather than sending Joey's half of the bill to Anna through Zelle/Venmo/etc, Joey can just "send" Anna money through the app. The app will keep track of who owes who how much, and anyone can query the app to see who should pay for the next thing so that people stay mostly even.

# Development

How to run locally

1. Install dependencies

```bash
$ poetry install
```

2. Run 
```bash
poetry run python -m uvicorn app.main:app --reload
```

### Pre-commit hooks

How to run pre-commit hooks:

```bash
$ poetry run pre-commit run --all-files
```

## Feature ideas

- [ ] Recurring IOU
- [ ] Split bill between everyone (or specified users in chat)
- [ ] Group participants (e.g., by household)
- [ ] Settle IOUs (e.g., figure out who owes who how much and add negative amount to transactions)
- [ ] List all transactions
- [ ] Request an IOU (have someone confirm? or nah?)
- [ ] When validating users, suggest a close match, e.g., "did you mean XYZ?"
- [ ] Validate that users are a member of the conversation
    - [ ] First stage is to have this in the bot (since that has awareness of the group text). Second level of maturity is to handle it in the backend
- [ ] Add split endpoint to split a charge between all chat members (or specified people)
