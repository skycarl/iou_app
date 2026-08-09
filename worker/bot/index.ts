import { Bot } from 'grammy';
import type { UserFromGetMe } from 'grammy/types';
import { conversations, createConversation } from '@grammyjs/conversations';
import { createD1Storage } from '../db/sessionStore.js';
import { getActiveEntriesForUser } from '../db/entries.js';
import { setConversationId } from '../db/users.js';
import { chunkText, formatTransactions } from '../domain/format.js';
import { VERSION } from '../version.js';
import type { BotContext, ConversationContext, Env } from '../types.js';
import { authorize } from './auth.js';
import { BILL_CONVERSATION, billFlow } from '../flows/bill.js';
import { QUERY_CONVERSATION, queryFlow } from '../flows/query.js';
import { SEND_CONVERSATION, sendFlow } from '../flows/send.js';
import { SETTLE_CONVERSATION, settleFlow } from '../flows/settle.js';
import { SPLIT_CONVERSATION, splitFlow } from '../flows/split.js';
import {
  ALREADY_REGISTERED,
  GENERIC_ERROR,
  HELLO,
  HELP,
  NOTHING_TO_CANCEL,
  REGISTRATION_SUCCESSFUL,
} from './strings.js';

/** A guided flow left half-finished expires rather than trapping the user forever. */
const CONVERSATION_TIMEOUT_MS = 15 * 60 * 1000;

/**
 * `getMe` is the same for the life of the deployment, so cache it across
 * requests on the same isolate instead of paying a Telegram round trip per
 * update. This is deployment-wide data, never request state.
 */
let cachedBotInfo: UserFromGetMe | undefined;

export async function createBot(
  env: Env,
  botInfo: UserFromGetMe | undefined = cachedBotInfo,
): Promise<Bot<BotContext>> {
  const bot = new Bot<BotContext>(env.TELEGRAM_BOT_TOKEN, { botInfo });
  if (botInfo === undefined) {
    await bot.init();
    cachedBotInfo = bot.botInfo;
  }

  bot.use(authorize(env));

  bot.use(
    conversations<BotContext, ConversationContext>({
      storage: {
        type: 'key',
        version: 1,
        adapter: createD1Storage(env.DB),
        // Per chat *and* per user, matching python-telegram-bot's default so
        // two people in a group chat cannot walk into each other's flow.
        getStorageKey: (ctx) =>
          ctx.chat === undefined || ctx.from === undefined
            ? undefined
            : `${ctx.chat.id}:${ctx.from.id}`,
      },
    }),
  );

  const flows = [
    [SEND_CONVERSATION, sendFlow(env)],
    [BILL_CONVERSATION, billFlow(env)],
    [QUERY_CONVERSATION, queryFlow(env)],
    [SPLIT_CONVERSATION, splitFlow(env)],
    [SETTLE_CONVERSATION, settleFlow(env)],
  ] as const;

  for (const [id, builder] of flows) {
    bot.use(
      createConversation(builder, {
        id,
        maxMillisecondsToWait: CONVERSATION_TIMEOUT_MS,
      }),
    );
  }

  bot.command('start', async (ctx) => {
    const user = ctx.iouUser;
    if (user.conversation_id !== null && user.conversation_id !== '') {
      await ctx.reply(ALREADY_REGISTERED);
      return;
    }
    if (ctx.chat === undefined) return;
    try {
      await setConversationId(env.DB, user.username, String(ctx.chat.id));
    } catch (error) {
      console.error({ message: 'registration failed', error: String(error) });
      await ctx.reply(GENERIC_ERROR);
      return;
    }
    await ctx.reply(REGISTRATION_SUCCESSFUL);
  });

  bot.command('send', async (ctx) => ctx.conversation.enter(SEND_CONVERSATION));
  bot.command('bill', async (ctx) => ctx.conversation.enter(BILL_CONVERSATION));
  bot.command('query', async (ctx) => ctx.conversation.enter(QUERY_CONVERSATION));
  bot.command('split', async (ctx) => ctx.conversation.enter(SPLIT_CONVERSATION));
  bot.command('settle', async (ctx) => ctx.conversation.enter(SETTLE_CONVERSATION));

  bot.command('cancel', async (ctx) => {
    await ctx.reply(NOTHING_TO_CANCEL);
  });

  bot.command('list', async (ctx) => {
    const username = ctx.iouUser.username;
    let entries;
    try {
      entries = await getActiveEntriesForUser(env.DB, username);
    } catch (error) {
      console.error({ message: 'list failed', error: String(error) });
      await ctx.reply(GENERIC_ERROR);
      return;
    }
    if (entries.length === 0) {
      await ctx.reply('You have no transactions.');
      return;
    }
    for (const chunk of chunkText(formatTransactions(entries, username))) {
      await ctx.reply(chunk);
    }
  });

  bot.command('hello', async (ctx) => {
    await ctx.reply(HELLO);
  });

  bot.command('help', async (ctx) => {
    await ctx.reply(HELP);
  });

  bot.command('version', async (ctx) => {
    await ctx.reply(`App version: ${VERSION}`);
  });

  // No `bot.catch` here: grammY only consults that handler from the polling
  // loop, so under `webhookCallback` it would be dead code. Middleware errors
  // are handled where they actually surface, in worker/index.ts.
  return bot;
}
