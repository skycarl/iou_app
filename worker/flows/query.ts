import { getActiveEntriesBetween } from '../db/entries.js';
import { computeIouStatus } from '../domain/balance.js';
import { formatMoney } from '../domain/money.js';
import {
  conversationIdFor,
  listUsernames,
  usernameKeyboard,
  waitForSelection,
} from '../bot/helpers.js';
import { notRegistered } from '../bot/strings.js';
import type { ConversationContext, Env, IouConversation } from '../types.js';

export const QUERY_CONVERSATION = 'query';
const USER1_PREFIX = 'QUERY_USER1_';
const USER2_PREFIX = 'QUERY_USER2_';

/** /query — net balance between any two authorized users. */
export function queryFlow(env: Env) {
  return async function queryConversation(
    conversation: IouConversation,
    ctx: ConversationContext,
  ): Promise<void> {
    const chatId = ctx.chatId;
    if (chatId === undefined) return;

    const everyone = await conversation.external(() => listUsernames(env.DB));
    if (everyone.length < 2) {
      await ctx.reply('There are not enough users to query.');
      return;
    }

    await ctx.reply('Query: Select the first user:', {
      reply_markup: usernameKeyboard(everyone, USER1_PREFIX, everyone.length),
    });

    const first = await waitForSelection(conversation, USER1_PREFIX);
    const user1 = first.value;

    const user1ChatId = await conversation.external(() => conversationIdFor(env.DB, user1));
    if (user1ChatId === null) {
      await first.ctx.api.sendMessage(chatId, notRegistered(user1));
      return;
    }

    const remaining = everyone.filter((username) => username !== user1);
    await first.ctx.editMessageText(`First user: @${user1}. Now select the second user:`, {
      reply_markup: usernameKeyboard(remaining, USER2_PREFIX, 3),
    });

    const second = await waitForSelection(conversation, USER2_PREFIX);
    const user2 = second.value;

    const user2ChatId = await conversation.external(() => conversationIdFor(env.DB, user2));
    if (user2ChatId === null) {
      await second.ctx.api.sendMessage(chatId, notRegistered(user2));
      return;
    }

    try {
      const entries = await conversation.external(() =>
        getActiveEntriesBetween(env.DB, user1, user2),
      );
      const status = computeIouStatus(entries, user1, user2);
      await second.ctx.editMessageText(
        `@${status.owingUser} owes @${status.owedUser} ${formatMoney(status.amount)}`,
      );
    } catch (error) {
      console.error({ message: 'query failed', error: String(error) });
      await second.ctx.editMessageText(
        `❌ Error: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  };
}
