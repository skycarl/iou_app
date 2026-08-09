<h1 align="center">
🧾 IOU App
</h1>

<h2 align="center">
A Telegram bot for tracking IOUs between friends
</h2>

## Overview

The IOU App helps friends, roommates and groups keep track of who owes whom
without anyone actually moving money around. Everything happens in Telegram:
record what you owe, bill someone, split a bill among several people, check a
balance, and settle up — each through a guided flow with tappable buttons.

## Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Register with the bot |
| `/send` | Record that you owe someone |
| `/bill` | Record that someone owes you |
| `/query` | Check the balance between two users |
| `/split` | Split a bill among several people |
| `/settle` | Clear all transactions with another user |
| `/list` | Show your transaction history |
| `/cancel` | Abandon the flow you are in |
| `/help` | Show available commands |
| `/hello` | Say hello |
| `/version` | Show the deployed version |

Membership is a manually maintained allowlist — there is no self-signup. See
[Adding a user](#adding-a-user).

## Architecture

A single Cloudflare Worker, written in TypeScript:

- **[grammY](https://grammy.dev)** handles the Telegram Bot API, with
  `@grammyjs/conversations` driving the multi-step flows.
- **D1** (Cloudflare's SQLite) stores users, entries and conversation state.
  Schema lives in `migrations/`.
- The bot runs on **webhooks**, not polling, so the Worker only executes when
  an update arrives.

```
worker/
  index.ts       fetch handler: /healthcheck and the webhook route
  bot/           bot wiring, authorization, shared helpers, user-facing strings
  flows/         the five guided conversations
  domain/        amounts, balances, splits, formatting — no I/O
  db/            D1 queries and the conversation session store
```

Amounts are stored as `REAL` and rounded only for display. Settling
soft-deletes entries (`deleted = 1`) rather than removing them.

## Security model

The Worker exposes exactly two routes. `/healthcheck` returns a status and
version and touches no data. Everything else is the webhook, at
`/telegram/<random-segment>` — the segment is in `worker/webhookPath.ts`.

Knowing that URL is not sufficient. Telegram echoes back a shared secret in the
`X-Telegram-Bot-Api-Secret-Token` header, which the Worker compares against
`TELEGRAM_WEBHOOK_SECRET` in constant time; anything else gets a 401. Beyond
that, every update's sender must resolve to a row in `users`, matched on their
numeric Telegram id where one is recorded, so a username change neither locks
someone out nor lets anyone rename their way in. Authorization fails closed if
the database is unreachable.

## Local development

```bash
npm install
npx wrangler d1 migrations apply iou-app --local
npx wrangler dev
```

Put local secrets in `.dev.vars` (gitignored):

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_SECRET=...
```

`wrangler dev` uses a local D1 by default, so nothing you do touches production
data. Seed the local database with `npx wrangler d1 execute iou-app --local
--command "..."`.

## Testing

```bash
npm test          # vitest, against a real local D1
npx tsc --noEmit  # typecheck
```

Tests cover the amount parser, balance and split maths, D1 queries and
settlement, webhook authentication, allowlist gating, and all five guided flows
driven end to end through real Telegram updates.

## Deployment

Push to `main`. The `Deploy Worker` GitHub Actions workflow typechecks, runs the
tests, applies any pending D1 migrations, and then deploys. It needs two repo
secrets: `CLOUDFLARE_API_TOKEN` (with Workers and D1 edit permission) and
`CLOUDFLARE_ACCOUNT_ID`.

The Worker itself needs two secrets, set once with `npx wrangler secret put`:

| Secret | Purpose |
|--------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/botfather) |
| `TELEGRAM_WEBHOOK_SECRET` | Shared secret registered with `setWebhook` and verified on every update |

If you change either the webhook path or the secret, re-register the webhook
with Telegram's `setWebhook`, passing the full URL and a matching
`secret_token`. If the two disagree, every update is rejected with a 401.

## Adding a user

New users are added by hand — the bot has no signup flow:

```bash
npx wrangler d1 execute iou-app --remote \
  --command "INSERT INTO users (username, conversation_id, telegram_user_id) VALUES ('their_telegram_username', NULL, NULL)"
```

They then send `/start` to the bot, which records the chat to message them in
and binds their numeric Telegram id. Until they do, other people's flows will
report them as not registered.

## Examples

**Dinner split.** Alex pays $60 for three. `/split` divides it and creates two
IOUs: Sam owes Alex $20, Jordan owes Alex $20.

**Ongoing expenses.** Sam bills Jordan $25 for groceries; later Jordan sends Sam
$15 for gas. `/query` reports that Jordan owes Sam $10.

**Settlement.** Once real money changes hands, `/settle` clears everything
between the two of them and starts them over at zero.
