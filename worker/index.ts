import { webhookCallback } from 'grammy';
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

    try {
      const bot = await createBot(env);
      return await webhookCallback(bot, 'cloudflare-mod', {
        secretToken: expected,
        onTimeout: 'return',
      })(request);
    } catch (error) {
      // Telegram retries on a non-2xx, which would replay a partially applied
      // update, so log and acknowledge instead.
      console.error({ message: 'webhook handling failed', error: String(error) });
      return new Response('ok');
    }
  },
} satisfies ExportedHandler<Env>;
