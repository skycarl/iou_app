import { env } from 'cloudflare:test';
import type { Bot } from 'grammy';
import type { Update, UserFromGetMe } from 'grammy/types';
import { beforeEach, describe, expect, it } from 'vitest';
// The bundled build, not the TypeScript source — see test/globalSetup.ts.
import { createBot } from './generated/bot.mjs';
import { getActiveEntriesBetween, getActiveEntriesForUser } from '../worker/db/entries.js';
import type { BotContext } from '../worker/types.js';

const BOT_INFO = {
  id: 42,
  is_bot: true,
  first_name: 'IOU',
  username: 'iou_test_bot',
  can_join_groups: true,
  can_read_all_group_messages: false,
  supports_inline_queries: false,
} as UserFromGetMe;

const ALICE = { id: 100, username: 'alice', chat: 500 };
const BOB = { id: 600, username: 'bob', chat: 600 };

interface ApiCall {
  method: string;
  payload: Record<string, unknown>;
}

/**
 * Drives real updates through the real bot, capturing outgoing Bot API calls.
 * Conversation state goes through the D1 `sessions` table, so this also covers
 * the storage adapter and the plugin's replay behaviour across updates.
 */
class BotHarness {
  readonly calls: ApiCall[] = [];
  private updateId = 0;
  private messageId = 0;

  constructor(private readonly bot: Bot<BotContext>) {}

  static async create(): Promise<BotHarness> {
    const harness = new BotHarness(await createBot(env, BOT_INFO));
    // The conversations plugin builds its own Api instances per replay, so a
    // grammY transformer would not see their calls. Stubbing fetch catches
    // every Telegram request no matter which Api instance issues it.
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const body = input instanceof Request ? await input.text() : String(init?.body ?? '{}');
      const method = url.slice(url.lastIndexOf('/') + 1);
      harness.calls.push({ method, payload: JSON.parse(body) as Record<string, unknown> });
      return Response.json({ ok: true, result: harness.resultFor(method) });
    }) as typeof fetch;
    return harness;
  }

  private resultFor(method: string): unknown {
    if (method === 'sendMessage' || method === 'editMessageText') {
      return { message_id: ++this.messageId, date: 1_700_000_000, chat: { id: ALICE.chat } };
    }
    return true;
  }

  /** Everything sent since the last call, so assertions stay scoped to a step. */
  drain(): ApiCall[] {
    return this.calls.splice(0, this.calls.length);
  }

  async command(user: typeof ALICE, text: string): Promise<void> {
    await this.send(user, text, [{ type: 'bot_command', offset: 0, length: text.length }]);
  }

  async text(user: typeof ALICE, text: string): Promise<void> {
    await this.send(user, text, undefined);
  }

  private async send(
    user: typeof ALICE,
    text: string,
    entities: { type: string; offset: number; length: number }[] | undefined,
  ): Promise<void> {
    await this.bot.handleUpdate({
      update_id: ++this.updateId,
      message: {
        message_id: ++this.messageId,
        date: 1_700_000_000,
        chat: { id: user.chat, type: 'private', first_name: 'Test' },
        from: { id: user.id, is_bot: false, first_name: 'Test', username: user.username },
        text,
        entities,
      },
    } as Update);
  }

  async tap(user: typeof ALICE, data: string): Promise<void> {
    await this.bot.handleUpdate({
      update_id: ++this.updateId,
      callback_query: {
        id: `cb${this.updateId}`,
        chat_instance: 'ci',
        data,
        from: { id: user.id, is_bot: false, first_name: 'Test', username: user.username },
        message: {
          message_id: this.messageId,
          date: 1_700_000_000,
          chat: { id: user.chat, type: 'private', first_name: 'Test' },
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

beforeEach(async () => {
  await env.DB.batch([
    env.DB.prepare('DELETE FROM entries'),
    env.DB.prepare('DELETE FROM sessions'),
    env.DB.prepare('DELETE FROM users'),
  ]);
  await env.DB.batch([
    env.DB.prepare('INSERT INTO users VALUES (?, ?, ?)').bind('alice', String(ALICE.chat), ALICE.id),
    env.DB.prepare('INSERT INTO users VALUES (?, ?, ?)').bind('bob', String(BOB.chat), BOB.id),
  ]);
});

describe('/send', () => {
  it('walks recipient, amount and description, then writes the entry', async () => {
    const harness = await BotHarness.create();

    await harness.command(ALICE, '/send');
    const prompt = harness.drain();
    expect(textsOf(prompt)).toEqual(['Select a recipient:']);
    expect(JSON.stringify(prompt[0]?.payload.reply_markup)).toContain('SEND_RECIPIENT_bob');

    await harness.tap(ALICE, 'SEND_RECIPIENT_bob');
    expect(textsOf(harness.drain()).join()).toContain('Enter the amount you want to send');

    await harness.text(ALICE, '$1,234.50');
    expect(textsOf(harness.drain()).join()).toContain('Enter a description');

    await harness.text(ALICE, 'rent');
    const done = textsOf(harness.drain());

    expect(done.some((text) => text === '✅ You sent @bob $1,234.50 for rent')).toBe(true);
    expect(done.some((text) => text === '@alice sent you $1,234.50 for rent')).toBe(true);

    const entries = await getActiveEntriesBetween(env.DB, 'alice', 'bob');
    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({
      sender: 'alice',
      recipient: 'bob',
      amount: 1234.5,
      description: 'rent',
      deleted: 0,
    });
  });

  it('reprompts on an unparseable amount instead of dropping the flow', async () => {
    const harness = await BotHarness.create();
    await harness.command(ALICE, '/send');
    await harness.tap(ALICE, 'SEND_RECIPIENT_bob');
    harness.drain();

    await harness.text(ALICE, '12.34.56');
    expect(textsOf(harness.drain()).join()).toContain('Unable to parse amount');

    await harness.text(ALICE, 'twenty');
    expect(textsOf(harness.drain()).join()).toContain('contains invalid characters');

    await harness.text(ALICE, '20');
    await harness.text(ALICE, 'lunch');

    const entries = await getActiveEntriesBetween(env.DB, 'alice', 'bob');
    expect(entries).toHaveLength(1);
    expect(entries[0]?.amount).toBe(20);
  });

  it('abandons the flow on /cancel and writes nothing', async () => {
    const harness = await BotHarness.create();
    await harness.command(ALICE, '/send');
    await harness.tap(ALICE, 'SEND_RECIPIENT_bob');
    harness.drain();

    await harness.text(ALICE, '/cancel');
    expect(textsOf(harness.drain())).toContain('Cancelled.');

    expect(await getActiveEntriesForUser(env.DB, 'alice')).toHaveLength(0);
    // The conversation is over, so a stray message is no longer captured.
    await harness.text(ALICE, '20');
    expect(harness.drain()).toEqual([]);
  });
});

describe('/bill', () => {
  it('records the other user as the one who owes', async () => {
    const harness = await BotHarness.create();
    await harness.command(ALICE, '/bill');
    await harness.tap(ALICE, 'BILL_SENDER_bob');
    await harness.text(ALICE, '15');
    await harness.text(ALICE, 'tickets');

    const entries = await getActiveEntriesBetween(env.DB, 'alice', 'bob');
    expect(entries[0]).toMatchObject({ sender: 'bob', recipient: 'alice', amount: 15 });
  });
});

describe('/settle', () => {
  it('shows the balance, waits for confirmation, then soft-deletes everything', async () => {
    const harness = await BotHarness.create();

    await harness.command(ALICE, '/send');
    await harness.tap(ALICE, 'SEND_RECIPIENT_bob');
    await harness.text(ALICE, '30');
    await harness.text(ALICE, 'dinner');
    harness.drain();

    await harness.command(ALICE, '/settle');
    await harness.tap(ALICE, 'SETTLE_USER_bob');
    const summary = textsOf(harness.drain()).join();
    expect(summary).toContain('@alice owes @bob $30.00');
    expect(summary).toContain('This will erase all transaction history between you.');

    await harness.tap(ALICE, 'SETTLE_CONFIRM_YES');
    const result = textsOf(harness.drain()).join();
    expect(result).toContain('1 transaction(s) totaling $30.00 have been settled');

    expect(await getActiveEntriesBetween(env.DB, 'alice', 'bob')).toHaveLength(0);
    const row = await env.DB.prepare('SELECT deleted FROM entries').first<{ deleted: number }>();
    expect(row?.deleted).toBe(1);
  });

  it('keeps the entries when the user declines', async () => {
    const harness = await BotHarness.create();
    await harness.command(ALICE, '/bill');
    await harness.tap(ALICE, 'BILL_SENDER_bob');
    await harness.text(ALICE, '10');
    await harness.text(ALICE, 'x');

    await harness.command(ALICE, '/settle');
    await harness.tap(ALICE, 'SETTLE_USER_bob');
    harness.drain();
    await harness.tap(ALICE, 'SETTLE_CONFIRM_NO');

    expect(textsOf(harness.drain())).toContain('Settlement cancelled.');
    expect(await getActiveEntriesBetween(env.DB, 'alice', 'bob')).toHaveLength(1);
  });

  it('refuses to settle when nothing is outstanding', async () => {
    const harness = await BotHarness.create();
    await harness.command(ALICE, '/settle');
    await harness.tap(ALICE, 'SETTLE_USER_bob');

    expect(textsOf(harness.drain()).join()).toContain(
      'No outstanding transactions between you and @bob to settle.',
    );
  });
});

describe('/split', () => {
  it('charges each non-payer participant an even share', async () => {
    await env.DB.prepare('INSERT INTO users VALUES (?, ?, ?)').bind('carol', '700', 700).run();
    const harness = await BotHarness.create();

    await harness.command(ALICE, '/split');
    await harness.tap(ALICE, 'SPLIT_PAYER_alice');
    await harness.text(ALICE, '60');
    await harness.text(ALICE, 'dinner');
    harness.drain();

    // Only the initiator and the payer start selected — here both are alice.
    await harness.tap(ALICE, 'SPLIT_PART_TOGGLE_bob');
    await harness.tap(ALICE, 'SPLIT_PART_TOGGLE_carol');
    await harness.tap(ALICE, 'SPLIT_PART_DONE');
    expect(textsOf(harness.drain())).toContain('✅ Split successful!');

    const entries = await getActiveEntriesForUser(env.DB, 'alice');
    expect(entries).toHaveLength(2);
    expect(entries.every((entry) => entry.recipient === 'alice')).toBe(true);
    expect(entries.every((entry) => entry.amount === 20)).toBe(true);
    expect(entries[0]?.description).toBe(
      'Split: dinner | Total: $60.00 | Participants: alice, bob, carol',
    );
  });

  it('will not let the payer be removed from the split', async () => {
    const harness = await BotHarness.create();
    await harness.command(ALICE, '/split');
    await harness.tap(ALICE, 'SPLIT_PAYER_bob');
    await harness.text(ALICE, '10');
    await harness.text(ALICE, 'x');
    harness.drain();

    await harness.tap(ALICE, 'SPLIT_PART_TOGGLE_bob');
    expect(textsOf(harness.drain()).join()).toContain(
      'The payer @bob cannot be removed from the split.',
    );
  });
});

describe('/query and /list', () => {
  it('reports the net balance between two users', async () => {
    const harness = await BotHarness.create();
    await harness.command(ALICE, '/send');
    await harness.tap(ALICE, 'SEND_RECIPIENT_bob');
    await harness.text(ALICE, '25');
    await harness.text(ALICE, 'x');
    harness.drain();

    await harness.command(ALICE, '/query');
    await harness.tap(ALICE, 'QUERY_USER1_alice');
    await harness.tap(ALICE, 'QUERY_USER2_bob');

    expect(textsOf(harness.drain())).toContain('@alice owes @bob $25.00');
  });

  it('lists the caller’s transactions', async () => {
    const harness = await BotHarness.create();
    await harness.command(ALICE, '/list');
    expect(textsOf(harness.drain())).toContain('You have no transactions.');

    await harness.command(ALICE, '/bill');
    await harness.tap(ALICE, 'BILL_SENDER_bob');
    await harness.text(ALICE, '12.34');
    await harness.text(ALICE, 'coffee');
    harness.drain();

    await harness.command(ALICE, '/list');
    const listing = textsOf(harness.drain()).join();
    expect(listing).toContain('📋 Your Transaction History:');
    expect(listing).toContain('➕ @bob owes you $12.34');
    expect(listing).toContain('📝 coffee');
  });
});

describe('simple commands', () => {
  it('answers /hello, /help and /version', async () => {
    const harness = await BotHarness.create();

    await harness.command(ALICE, '/hello');
    expect(textsOf(harness.drain())).toContain('Hello to yourself!');

    await harness.command(ALICE, '/help');
    expect(textsOf(harness.drain()).join()).toContain('To send money: /send');

    await harness.command(ALICE, '/version');
    expect(textsOf(harness.drain())).toContain('App version: 1.0.0');
  });

  it('registers an allowlisted user who has never started the bot', async () => {
    await env.DB.prepare('UPDATE users SET conversation_id = NULL WHERE username = ?')
      .bind('alice')
      .run();
    const harness = await BotHarness.create();

    await harness.command(ALICE, '/start');
    expect(textsOf(harness.drain())).toContain('Registration successful!');

    await harness.command(ALICE, '/start');
    expect(textsOf(harness.drain())).toContain('You are already registered.');
  });
});
