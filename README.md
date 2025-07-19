<h1 align="center">
🧾 IOU App
</h1>

<h2 align="center">
A simple IOU tracking system with Telegram bot integration
</h2>

## Overview

The IOU App is a simple debt tracking application that helps friends, roommates, and groups manage shared expenses and IOUs. It consists of a FastAPI backend with a Telegram bot interface, allowing users to send money, split bills, query balances, and settle debts through an intuitive chat experience, all without exchanging actual money.

## Key Features

### 💸 **Core Functionality**
- **Send Money**: Record payments between users
- **Bill Users**: Create IOUs when someone owes you money
- **Query Status**: Check who owes what between any two users
- **Split Bills**: Automatically divide expenses among multiple participants
- **Settle Debts**: Clear all transactions between two users (used when actual money is exchanged to settle debts)
- **Transaction History**: View complete payment history

### 🤖 **Telegram Bot Interface**
- Interactive inline keyboards for easy user selection
- Guided conversation flows for all operations
- User authorization and registration system
- Real-time notifications
- Support for both private and group chats

### 🏗️ **Technical Features**
- FastAPI REST API backend
- AWS DynamoDB for data persistence with caching
- Docker containerization for easy deployment
- Comprehensive test coverage
- Code quality enforcement with ruff linting
- Pre-commit hooks for development workflow

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │───▶│   FastAPI App   │───▶│   DynamoDB      │
│   (User Interface) │    │   (API Backend)   │    │   (Data Storage)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Setup Instructions

### Prerequisites
- Docker and Docker Compose
- AWS account with DynamoDB access
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### 1. Environment Configuration

Create a `.env` file in the root directory with the following variables:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your-bot-token-here
X_TOKEN=your-api-security-token

# API Configuration
APP_URL=http://app:8000/api

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-west-2

# DynamoDB Tables
DDB_DATA_TABLE_NAME=iou_app_dev
DDB_USERS_TABLE_NAME=iou_users_dev

# Docker Configuration
HOST_PATH=/path/to/your/project
```

### 2. Launch Application

```bash
# Start all services with Docker Compose
docker compose up -d
```

This will start:
- **FastAPI app** on `http://localhost:8000`
- **Telegram bot** connected to your configured bot token

### 3. Verify Setup

Check that services are running:
```bash
# Check API health
curl http://localhost:8000/healthcheck

# View logs
docker compose logs -f
```

## API Endpoints

The FastAPI backend provides the following REST endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/healthcheck` | Service health status |
| `GET` | `/version` | Application version |
| `GET` | `/api/entries` | List transactions (with optional user filters) |
| `POST` | `/api/entries` | Create new transaction |
| `GET` | `/api/entries/{id}` | Get specific transaction |
| `DELETE` | `/api/entries/{id}` | Soft delete transaction |
| `GET` | `/api/iou_status/` | Get IOU status between two users |
| `POST` | `/api/split` | Split bill among participants |
| `POST` | `/api/settle` | Settle all debts between two users |
| `GET` | `/api/users/` | List all users |
| `POST` | `/api/users` | Create new user |
| `GET` | `/api/users/{username}` | Get user details |
| `PUT` | `/api/users/{username}` | Update user information |

All API endpoints require the `X-Token` header for authentication.

## Telegram Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Register with the bot | `/start` |
| `/send` | Send money to another user | Guided flow |
| `/bill` | Bill someone for money they owe | Guided flow |
| `/query` | Check IOU status between users | Guided flow |
| `/split` | Split a bill among multiple people | Guided flow |
| `/settle` | Settle all debts with another user | Guided flow |
| `/list` | View your transaction history | `/list` |
| `/help` | Show available commands | `/help` |
| `/version` | Show app version | `/version` |

All commands use interactive inline keyboards for easy navigation.

## Development

### Prerequisites
- Python 3.13+
- Poetry for dependency management

### Setup Development Environment

```bash
# Install dependencies
make install

# Run tests
make test

# Run linting
make lint

# Auto-fix linting issues
make lint-fix

# Run pre-commit hooks
make pre-commit

# Start development server
make run
```

### Development Workflow

**Always follow this workflow after making code changes:**

1. **Run tests**: `make test`
2. **Run linting**: `make lint`
3. **Fix linting issues**: `make lint-fix`
4. **Run pre-commit hooks**: `make pre-commit`

### Available Make Commands

- `make install` - Install dependencies with Poetry
- `make test` - Run pytest test suite
- `make lint` - Check code quality with ruff
- `make lint-fix` - Auto-fix ruff issues
- `make run` - Start FastAPI development server
- `make pre-commit` - Run all pre-commit hooks
- `make help` - Show available commands

## Example Use Cases

### Scenario 1: Dinner Split
1. Alex pays $60 for dinner for 3 people
2. Use `/split` command to divide among Alex, Sam, and Jordan
3. Bot creates IOUs: Sam owes Alex $20, Jordan owes Alex $20

### Scenario 2: Ongoing Expenses
1. Sam uses `/bill` to bill Jordan $25 for groceries
2. Later, Jordan uses `/send` to pay Sam $15 for gas
3. Use `/query` to check: Jordan owes Sam $10 total

### Scenario 3: Settlement
1. After many transactions, use `/settle` between Sam and Jordan
2. Bot calculates final amount and clears all transactions
3. Fresh start for future IOUs

## Data Storage

- **Primary Storage**: AWS DynamoDB for implementation ease
- **Caching**: In-memory caching with TTL for performance
- **Data Structure**: Separate tables for transactions and users

## Deployment

The application is designed for containerized deployment:

```bash
# Production deployment
docker compose -f docker-compose.yml up -d

# View application logs
docker compose logs -f app

# View bot logs
docker compose logs -f bot
```

## Security

- **API Authentication**: X-Token header validation
- **User Authorization**: Telegram users must be pre-registered
- **Environment Variables**: Sensitive configuration in `.env` files
- **AWS IAM**: Proper IAM roles for DynamoDB access

## Contributing

1. Follow the development workflow outlined above
2. Ensure all tests pass and linting is clean
3. Pre-commit hooks must pass before committing
4. Use Poetry for dependency management
