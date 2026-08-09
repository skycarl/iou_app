import { BotError, webhookCallback } from 'grammy';
import type { Context } from 'grammy';
import { createBot } from './bot/index.js';
import { WEBHOOK_PATH } from './webhookPath.js';
import { VERSION } from './version.js';
import type { Env } from './types.js';

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

const SOMETHING_WENT_WRONG =
  '❌ Something went wrong. If you were in the middle of a guided flow it has ' +
  'been cancelled — please start it again.';

/** What the user was doing, so a failure is traceable to a command. */
function describeAction(ctx: Context): string {
  const text = ctx.message?.text;
  if (text !== undefined) return text.split(/\s/)[0] ?? 'message';
  const data = ctx.callbackQuery?.data;
  if (data !== undefined) return `callback:${data}`;
  return 'update';
}

/**
 * Middleware errors surface here rather than through `bot.catch`: grammY only
 * consults its error handler from the polling loop, and `webhookCallback` goes
 * through `bot.handleUpdate`, which rethrows as a BotError.
 *
 * An error escaping a conversation makes the plugin discard its state, so the
 * user's half-finished flow is gone. Saying so beats leaving them staring at a
 * prompt that will never respond.
 */
async function handleBotError(error: BotError<Context>): Promise<void> {
  const ctx = error.ctx;
  console.error({
    message: 'update handling failed',
    update_id: ctx?.update?.update_id,
    chat_id: ctx?.chat?.id,
    username: ctx?.from?.username,
    action: ctx === undefined ? 'unknown' : describeAction(ctx),
    error: String(error.error),
  });

  // Best effort: whatever broke the update is quite likely to break this too.
  if (ctx?.chat === undefined) return;
  try {
    await ctx.reply(SOMETHING_WENT_WRONG);
  } catch (replyError) {
    console.error({ message: 'could not report failure', error: String(replyError) });
  }
}

/**
 * Constant-time string comparison. A plain `===` would leak how many leading
 * characters of the webhook secret an attacker has guessed.
 */
function secretsMatch(a: string, b: string): boolean {
  const encoder = new TextEncoder();
  const left = encoder.encode(a);
  const right = encoder.encode(b);
  if (left.byteLength !== right.byteLength) return false;
  return crypto.subtle.timingSafeEqual(left, right);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/healthcheck') {
      return json({ status: 'ok', version: VERSION });
    }

    if (url.pathname !== WEBHOOK_PATH) {
      return new Response('Not found', { status: 404 });
    }
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    // Knowing the URL is not enough: Telegram echoes back a shared secret that
    // was registered with setWebhook, and anything else is rejected outright.
    const presented = request.headers.get('X-Telegram-Bot-Api-Secret-Token');
    const expected = env.TELEGRAM_WEBHOOK_SECRET;
    if (
      typeof expected !== 'string' ||
      expected === '' ||
      presented === null ||
      !secretsMatch(presented, expected)
    ) {
      return new Response('Unauthorized', { status: 401 });
    }

    // Telegram retries on a non-2xx, which would replay a partially applied
    // update, so every failure below is logged and then acknowledged.
    try {
      const bot = await createBot(env);
      return await webhookCallback(bot, 'cloudflare-mod', {
        secretToken: expected,
        onTimeout: 'return',
      })(request);
    } catch (error) {
      if (error instanceof BotError) {
        await handleBotError(error);
      } else {
        console.error({ message: 'webhook handling failed', error: String(error) });
      }
      return new Response('ok');
    }
  },
} satisfies ExportedHandler<Env>;
