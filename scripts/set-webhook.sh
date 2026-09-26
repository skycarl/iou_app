#!/usr/bin/env bash
# Point the production Telegram bot at the Worker, rotating the webhook secret.
# Run after the Worker's URL changes (e.g. the account's workers.dev subdomain was renamed).
#
#   scripts/set-webhook.sh [base-url]      # default: https://iou-app.skycarl.workers.dev
#
# Prompts for the *production* bot token (from @BotFather) so it never lands in shell
# history. Generates a new TELEGRAM_WEBHOOK_SECRET, stores it on the Worker, then
# registers the webhook with Telegram using the same secret. Telegram holds undelivered
# updates for 24h and retries, so the few seconds between the two steps lose nothing.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE_URL="${1:-https://iou-app.skycarl.workers.dev}"
WEBHOOK_PATH=$(sed -nE "s/.*WEBHOOK_PATH = '([^']+)'.*/\1/p" worker/webhookPath.ts)
[ -n "$WEBHOOK_PATH" ] || { echo "Could not read WEBHOOK_PATH from worker/webhookPath.ts" >&2; exit 1; }

curl -fsS -o /dev/null "$BASE_URL/healthcheck" || { echo "$BASE_URL/healthcheck is not reachable; aborting." >&2; exit 1; }

read -rsp "Production TELEGRAM_BOT_TOKEN: " TOKEN; echo
BOT=$(curl -fsS "https://api.telegram.org/bot$TOKEN/getMe" | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["username"])') \
  || { echo "Token rejected by Telegram." >&2; exit 1; }
read -rp "Bot is @$BOT. Point it at $BASE_URL? [y/N] " ok
[ "$ok" = "y" ] || exit 1

SECRET=$(openssl rand -hex 32)
printf '%s' "$SECRET" | npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
curl -fsS "https://api.telegram.org/bot$TOKEN/setWebhook" \
  --data-urlencode "url=$BASE_URL$WEBHOOK_PATH" \
  --data-urlencode "secret_token=$SECRET" >/dev/null
echo "Webhook set. Status:"
curl -fsS "https://api.telegram.org/bot$TOKEN/getWebhookInfo" \
  | python3 -c 'import json,sys; r=json.load(sys.stdin)["result"]; print(" url host:", r["url"].split("/telegram/")[0]); print(" pending:", r.get("pending_update_count")); print(" last error:", r.get("last_error_message"))'
