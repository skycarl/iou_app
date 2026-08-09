# CLAUDE.md

IOU-tracking Telegram bot for a fixed group of friends, running entirely on Cloudflare Workers + D1. TypeScript, grammY (webhook mode), no frontend, no REST API. Migrated from a Python/FastAPI + polling-bot stack on a Raspberry Pi in August 2026 (PR #76/#77); the legacy data source (AWS DynamoDB `iou_app`/`iou_users`, us-west-2) is retained as a cold backup only.

## Commands

- `npm test` — vitest suite (flow tests run against an esbuild bundle built in `test/globalSetup.ts`, because Vite's module runner mishandles the CJS/ESM mix of `@grammyjs/conversations` + grammY; production is unaffected)
- `npx tsc --noEmit` — typecheck
- `npx wrangler dev` — local dev with a local D1; apply schema first with `npx wrangler d1 migrations apply iou-app --local`
- `npx wrangler deploy --dry-run` — build sanity check

## Deployment

**Every push to `main` is a live deploy** (`.github/workflows/deploy.yml`: typecheck → tests → D1 migrations → `wrangler deploy`). Don't push to main unasked. Repo secrets: `CLOUDFLARE_API_TOKEN` (needs Workers Edit + D1 Edit), `CLOUDFLARE_ACCOUNT_ID`. Worker secrets (via `wrangler secret put`): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`.

## Architecture

- `worker/index.ts` — fetch handler: `/healthcheck`, plus the Telegram webhook at a secret path (`worker/webhookPath.ts`). Every update must carry the correct `X-Telegram-Bot-Api-Secret-Token` header (timing-safe compare) or gets a 401.
- `worker/bot/` — grammY bot: commands, auth allowlist, keyboards. `worker/flows/` — the 5 guided conversations (`send`, `bill`, `query`, `split`, `settle`) via `@grammyjs/conversations`, state persisted in the D1 `sessions` table (`worker/db/sessionStore.ts`), keyed per chat *and* per user.
- `worker/domain/` — ported business logic (balance, split, money). `worker/db/` — D1 access.
- `migrations/` — D1 migrations, applied by CI on deploy.

## Invariants and gotchas

- **This is a private app.** Only usernames in the D1 `users` table may use the bot; there is deliberately no self-signup. Add a user: `npx wrangler d1 execute iou-app --remote --command "INSERT INTO users (username) VALUES ('name')"`. Fail closed on auth/DB errors.
- Impersonation guard: once a user's `telegram_user_id` is backfilled, a username match with a different id is refused. Don't weaken this.
- Money is `REAL` with round-half-to-even display rounding (matches the legacy Python `round()`); amounts ported through `worker/domain/amount.ts` must keep legacy parsing semantics ("$1,234.50" ok, "12.34.56" rejected, any letter rejected).
- `bot.catch` does NOT fire in webhook mode — middleware errors are handled in `worker/index.ts` (`handleBotError`). Don't reintroduce `bot.catch` and assume it works.
- grammY API transformers don't reach calls made inside conversations (the plugin builds its own `Api`); use the conversation plugin's `plugins` option instead.
- Settle soft-deletes **all** active entries between two users — never test it to completion against the production DB.
- Testing against prod: only ever create entries between `skycarl` and `rigels`, description prefixed `[MIGRATION-TEST]`, and delete them afterwards.
