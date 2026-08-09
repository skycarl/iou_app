import { env } from 'cloudflare:test';
import type { Update } from 'grammy/types';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
// The bundled build, not the TypeScript source — see test/globalSetup.ts.
import { worker } from './generated/bot.mjs';
import { WEBHOOK_PATH } from '../worker/webhookPath.js';
import { getActiveEntriesForUser } from '../worker/db/entries.js';

const BASE = 'https://iou-app.example.workers.dev';
const SECRET = 'correct-webhook-secret';
const ALICE = { id: 100, username: 'alice', chat: 500 };

interface ApiCall {
  method: string;
  payload: Record<string, unknown>;
}

/**
 * Drives updates through the Worker's real fetch handler, so the entry point's
 * error handling is exercised rather than bypassed. Telegram is stubbed at
 * `fetch`, which lets a chosen method be made to fail mid-flow.
 */
class WebhookHarness {
  readonly calls: ApiCall[] = [];
  readonly failing = new Set<string>();
  private updateId = 0;
  private messageId = 0;

  install(): void {
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const body = input instanceof Request ? await input.text() : String(init?.body ?? '{}');
      const method = url.slice(url.lastIndexOf('/') + 1);
      this.calls.push({ method, payload: JSON.parse(body) as Record<string, unknown> });

      if (this.failing.has(method)) {
        return Response.json({
          ok: false,
          error_code: 500,
          description: 'Internal Server Error: telegram is having a moment',
        });
      }
      return Response.json({ ok: true, result: this.resultFor(method) });
    }) as typeof fetch;
  }

  private resultFor(method: string): unknown {
    if (method === 'getMe') {
      return { id: 42, is_bot: true, first_name: 'IOU', username: 'iou_test_bot' };
    }
    if (method === 'sendMessage' || method === 'editMessageText') {
      return { message_id: ++this.messageId, date: 1_700_000_000, chat: { id: ALICE.chat } };
    }
    return true;
  }

  drain(): ApiCall[] {
    return this.calls.splice(0, this.calls.length);
  }

  private post(update: Update): Promise<Response> {
    return worker.fetch(
      new Request(`${BASE}${WEBHOOK_PATH}`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'X-Telegram-Bot-Api-Secret-Token': SECRET,
        },
        body: JSON.stringify(update),
      }),
      env,
    );
  }

  command(text: string): Promise<Response> {
    return this.post({
      update_id: ++this.updateId,
      message: {
        message_id: ++this.messageId,
        date: 1_700_000_000,
        chat: { id: ALICE.chat, type: 'private', first_name: 'Test' },
        from: { id: ALICE.id, is_bot: false, first_name: 'Test', username: ALICE.username },
        text,
        entities: [{ type: 'bot_command', offset: 0, length: text.length }],
      },
    } as Update);
  }

  text(text: string): Promise<Response> {
    return this.post({
      update_id: ++this.updateId,
      message: {
        message_id: ++this.messageId,
        date: 1_700_000_000,
        chat: { id: ALICE.chat, type: 'private', first_name: 'Test' },
        from: { id: ALICE.id, is_bot: false, first_name: 'Test', username: ALICE.username },
        text,
      },
    } as Update);
  }

  tap(data: string): Promise<Response> {
    return this.post({
      update_id: ++this.updateId,
      callback_query: {
        id: `cb${this.updateId}`,
        chat_instance: 'ci',
        data,
        from: { id: ALICE.id, is_bot: false, first_name: 'Test', username: ALICE.username },
        message: {
          message_id: this.messageId,
          date: 1_700_000_000,
          chat: { id: ALICE.chat, type: 'private', first_name: 'Test' },
        },
      },
    } as Update);
  }
}

function textsOf(calls: ApiCall[]): string[] {
  return calls
    .filter((call) => call.method === 'sendMessage' || call.method === 'editMessageText')
    .map((call) => String(call.payload.text));
}

let harness: WebhookHarness;

beforeEach(async () => {
  await env.DB.batch([
    env.DB.prepare('DELETE FROM entries'),
    env.DB.prepare('DELETE FROM sessions'),
    env.DB.prepare('DELETE FROM users'),
  ]);
  await env.DB.batch([
    env.DB.prepare('INSERT INTO users VALUES (?, ?, ?)').bind('alice', String(ALICE.chat), ALICE.id),
    env.DB.prepare('INSERT INTO users VALUES (?, ?, ?)').bind('bob', '600', 600),
  ]);
  harness = new WebhookHarness();
  harness.install();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('a Telegram API failure mid-flow', () => {
  it('tells the user instead of leaving them at a dead prompt', async () => {
    await harness.command('/send');
    harness.drain();

    harness.failing.add('editMessageText');
    const response = await harness.tap('SEND_RECIPIENT_bob');

    // Still a 200, or Telegram retries the update and replays it.
    expect(response.status).toBe(200);
    expect(textsOf(harness.drain())).toContain(
      '❌ Something went wrong. If you were in the middle of a guided flow it ' +
        'has been cancelled — please start it again.',
    );
  });

  it('logs which user and which action failed', async () => {
    const logged = vi.spyOn(console, 'error').mockImplementation(() => {});

    await harness.command('/send');
    harness.failing.add('editMessageText');
    await harness.tap('SEND_RECIPIENT_bob');

    const report = logged.mock.calls
      .map(([entry]) => entry as Record<string, unknown>)
      .find((entry) => entry?.message === 'update handling failed');

    expect(report).toBeDefined();
    expect(report?.username).toBe('alice');
    expect(report?.action).toBe('callback:SEND_RECIPIENT_bob');
    expect(String(report?.error)).toContain('Internal Server Error');
  });

  it('writes no entry and does not resume the broken flow', async () => {
    await harness.command('/send');
    harness.failing.add('editMessageText');
    await harness.tap('SEND_RECIPIENT_bob');
    harness.failing.clear();
    harness.drain();

    // If the flow were still alive this would be taken as the amount.
    await harness.text('20');
    await harness.text('rent');

    expect(await getActiveEntriesForUser(env.DB, 'alice')).toHaveLength(0);
  });

  it('still answers 200 when even the apology cannot be delivered', async () => {
    await harness.command('/send');
    harness.failing.add('editMessageText');
    harness.failing.add('sendMessage');

    const response = await harness.tap('SEND_RECIPIENT_bob');
    expect(response.status).toBe(200);
  });

  it('acknowledges a failure outside any conversation', async () => {
    harness.failing.add('sendMessage');
    const response = await harness.command('/hello');

    expect(response.status).toBe(200);
  });
});
