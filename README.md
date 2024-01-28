<h1 align="center">
🍲  IOU App
</h1>

<h2 align="center">
  Simple app for IOU's
</h2>

# ⚒️ Techologies Used

- Alembic: For Database Migrations.
- SQLAlchemy: For ORM.
- Pydantic: For Typing or Serialization.
- Pytests: For TDD or Unit Testing.
- Poetry: Python dependency management and packaging made easy. (Better than pip)
- Docker & docker-compose : For Virtualization.
- PostgreSQL: Database.
- PgAdmin: To interact with the Postgres database sessions.
- Loguru: Easiest logging ever done.

# 🚀 Up and run in 5 mins 🕙
Make sure you have docker and docker-compose installed [docker installation guide](https://docs.docker.com/compose/install/)
## Step 1
create **.env** file in root folder iou_app/.env
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

# 🎉 Your Production Ready FastAPI CRUD backend app is up and running on `localhost:8000`

- Swagger docs on `localhost:8000/docs`
<img src="https://github.com/rawheel/fastapi-boilerplate/blob/main/media/swagger%20docs.png" alt="fastapi boilerplate">

- GET request example

<img src="https://github.com/rawheel/fastapi-boilerplate/blob/main/media/swagger%20get%20docs.png" alt="fastapi boilerplate">


- PgAdmin on `localhost:5050`

<img src="https://github.com/rawheel/fastapi-boilerplate/blob/main/media/pgadmin.png" alt="fastapi boilerplate">


## TODO:

- Add split endpoint

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
- [x] Switch to postgreSQL database rather than sqlite

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
- [ ] Add split endpoint to split a charge between all chat members (or specified people)
