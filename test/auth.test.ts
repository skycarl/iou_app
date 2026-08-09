import { env } from 'cloudflare:test';
import { Bot } from 'grammy';
import type { Update, UserFromGetMe } from 'grammy/types';
import { beforeEach, describe, expect, it } from 'vitest';
import { authorize } from '../worker/bot/auth.js';
import { GENERIC_ERROR, UNAUTHORIZED, UNAUTHORIZED_CALLBACK } from '../worker/bot/strings.js';
import { getUserByUsername } from '../worker/db/users.js';
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

interface ApiCall {
  method: string;
  payload: Record<string, unknown>;
}

/** A bot whose outgoing API calls are captured instead of sent to Telegram. */
function buildBot() {
  const calls: ApiCall[] = [];
  const reached: string[] = [];

  const bot = new Bot<BotContext>('123456:test-token', { botInfo: BOT_INFO });
  bot.api.config.use(async (_prev, method, payload) => {
    calls.push({ method, payload: payload as Record<string, unknown> });
    return { ok: true, result: true } as never;
  });

  bot.use(authorize(env));
  bot.command('hello', async (ctx) => {
    reached.push(ctx.iouUser.username);
    await ctx.reply('Hello to yourself!');
  });
  bot.on('callback_query:data', async (ctx) => {
    reached.push(ctx.iouUser.username);
    await ctx.answerCallbackQuery();
  });

  return { bot, calls, reached };
}

function messageUpdate(from: { id: number; username?: string }): Update {
  return {
    update_id: 1,
    message: {
      message_id: 1,
      date: 1_700_000_000,
      chat: { id: 500, type: 'private', first_name: 'Test' },
      from: { id: from.id, is_bot: false, first_name: 'Test', username: from.username },
      text: '/hello',
      entities: [{ type: 'bot_command', offset: 0, length: 6 }],
    },
  } as Update;
}

function callbackUpdate(from: { id: number; username?: string }): Update {
  return {
    update_id: 2,
    callback_query: {
      id: 'cb1',
      chat_instance: 'ci',
      data: 'SEND_RECIPIENT_bob',
      from: { id: from.id, is_bot: false, first_name: 'Test', username: from.username },
    },
  } as Update;
}

beforeEach(async () => {
  await env.DB.prepare('DELETE FROM users').run();
  await env.DB.batch([
    env.DB.prepare('INSERT INTO users VALUES (?, ?, ?)').bind('alice', '500', null),
    env.DB.prepare('INSERT INTO users VALUES (?, ?, ?)').bind('bob', '600', 600),
  ]);
});

describe('allowlist gating', () => {
  it('lets an allowlisted user through to the handler', async () => {
    const { bot, calls, reached } = buildBot();
    await bot.handleUpdate(messageUpdate({ id: 100, username: 'alice' }));

    expect(reached).toEqual(['alice']);
    expect(calls[0]?.payload.text).toBe('Hello to yourself!');
  });

  it('refuses a user who is not in the users table', async () => {
    const { bot, calls, reached } = buildBot();
    await bot.handleUpdate(messageUpdate({ id: 999, username: 'mallory' }));

    expect(reached).toEqual([]);
    expect(calls).toHaveLength(1);
    expect(calls[0]?.method).toBe('sendMessage');
    expect(calls[0]?.payload.text).toBe(UNAUTHORIZED);
  });

  it('refuses a user with no Telegram username', async () => {
    const { bot, calls, reached } = buildBot();
    await bot.handleUpdate(messageUpdate({ id: 999 }));

    expect(reached).toEqual([]);
    expect(calls[0]?.payload.text).toBe('You must have a Telegram username to use this bot.');
  });

  it('refuses an unauthorized callback query with an alert, not a chat message', async () => {
    const { bot, calls, reached } = buildBot();
    await bot.handleUpdate(callbackUpdate({ id: 999, username: 'mallory' }));

    expect(reached).toEqual([]);
    expect(calls[0]?.method).toBe('answerCallbackQuery');
    expect(calls[0]?.payload.text).toBe(UNAUTHORIZED_CALLBACK);
    expect(calls[0]?.payload.show_alert).toBe(true);
  });

  it('backfills the numeric Telegram id the first time a user is seen', async () => {
    const { bot } = buildBot();
    await bot.handleUpdate(messageUpdate({ id: 100, username: 'alice' }));

    const alice = await getUserByUsername(env.DB, 'alice');
    expect(alice?.telegram_user_id).toBe(100);
  });

  it('matches on the numeric id even after a username change', async () => {
    const { bot, reached } = buildBot();
    await bot.handleUpdate(messageUpdate({ id: 600, username: 'bob_renamed' }));

    expect(reached).toEqual(['bob']);
  });

  it('does not let an impostor claim an allowlisted username already bound to another id', async () => {
    const { bot, calls, reached } = buildBot();
    await bot.handleUpdate(messageUpdate({ id: 777, username: 'bob' }));

    expect(reached).toEqual([]);
    expect(calls[0]?.payload.text).toBe(UNAUTHORIZED);
    const bob = await getUserByUsername(env.DB, 'bob');
    expect(bob?.telegram_user_id).toBe(600);
  });

  it('fails closed when the database is unreachable', async () => {
    const { bot, calls, reached } = buildBot();
    await env.DB.prepare('DROP TABLE users').run();

    await bot.handleUpdate(messageUpdate({ id: 100, username: 'alice' }));

    expect(reached).toEqual([]);
    expect(calls[0]?.payload.text).toBe(GENERIC_ERROR);
  });
});
