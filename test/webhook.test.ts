import { env } from 'cloudflare:test';
import { describe, expect, it } from 'vitest';
import worker from '../worker/index.js';
import { WEBHOOK_PATH } from '../worker/webhookPath.js';
import { VERSION } from '../worker/version.js';

const BASE = 'https://iou-app.example.workers.dev';

function post(path: string, secret?: string): Request {
  const headers = new Headers({ 'content-type': 'application/json' });
  if (secret !== undefined) headers.set('X-Telegram-Bot-Api-Secret-Token', secret);
  return new Request(`${BASE}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ update_id: 1 }),
  });
}

const call = (request: Request): Promise<Response> => worker.fetch(request, env);

describe('webhook route', () => {
  it('rejects an update with no secret token', async () => {
    const response = await call(post(WEBHOOK_PATH));
    expect(response.status).toBe(401);
  });

  it('rejects an update with the wrong secret token', async () => {
    const response = await call(post(WEBHOOK_PATH, 'not-the-secret'));
    expect(response.status).toBe(401);
  });

  it('rejects a token that is a prefix of the real one', async () => {
    const response = await call(post(WEBHOOK_PATH, 'correct-webhook-secre'));
    expect(response.status).toBe(401);
  });

  it('does not answer on the path without the random segment', async () => {
    const response = await call(post('/telegram', 'correct-webhook-secret'));
    expect(response.status).toBe(404);
  });

  it('does not answer on a guessed path segment', async () => {
    const response = await call(post('/telegram/00000000000000000000000000000000'));
    expect(response.status).toBe(404);
  });

  it('rejects a GET on the webhook path', async () => {
    const request = new Request(`${BASE}${WEBHOOK_PATH}`, { method: 'GET' });
    expect((await call(request)).status).toBe(405);
  });

  it('exposes nothing else', async () => {
    for (const path of ['/', '/entries', '/users', '/version']) {
      const request = new Request(`${BASE}${path}`);
      expect((await call(request)).status).toBe(404);
    }
  });
});

describe('healthcheck', () => {
  it('reports ok and the build version without auth', async () => {
    const response = await call(new Request(`${BASE}/healthcheck`));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: 'ok', version: VERSION });
  });

  it('reports version 1.0.0', () => {
    expect(VERSION).toBe('1.0.0');
  });
});
