import { InlineKeyboard } from 'grammy';
import { getActiveEntriesBetween, settleBetween } from '../db/entries.js';
import { computeIouStatus } from '../domain/balance.js';
import { formatMoney } from '../domain/money.js';
import {
  conversationIdFor,
  listUsernames,
  trySend,
  usernameKeyboard,
  waitForSelection,
} from '../bot/helpers.js';
import { notRegistered } from '../bot/strings.js';
import type { ConversationContext, Env, IouConversation } from '../types.js';

export const SETTLE_CONVERSATION = 'settle';
const USER_PREFIX = 'SETTLE_USER_';
const CONFIRM_PREFIX = 'SETTLE_CONFIRM_';

/** /settle — soft-delete every active entry between the caller and another user. */
export function settleFlow(env: Env) {
  return async function settleConversation(
    conversation: IouConversation,
    ctx: ConversationContext,
  ): Promise<void> {
    const me = ctx.from?.username;
    const chatId = ctx.chatId;
    if (me === undefined || chatId === undefined) return;

    const candidates = await conversation.external(() => listUsernames(env.DB, me));
    if (candidates.length === 0) {
      await ctx.reply('There is nobody else to settle with.');
      return;
    }

    await ctx.reply('Select the user you want to settle with:', {
      reply_markup: usernameKeyboard(candidates, USER_PREFIX, 3),
    });

    const selection = await waitForSelection(conversation, USER_PREFIX);
    const otherUser = selection.value;

    const otherChatId = await conversation.external(() => conversationIdFor(env.DB, otherUser));
    if (otherChatId === null) {
      await selection.ctx.api.sendMessage(chatId, notRegistered(otherUser));
      return;
    }

    const entries = await conversation.external(() =>
      getActiveEntriesBetween(env.DB, me, otherUser),
    );
    const status = computeIouStatus(entries, me, otherUser);

    if (status.amount === 0) {
      await selection.ctx.editMessageText(
        `No outstanding transactions between you and @${otherUser} to settle.`,
      );
      return;
    }

    const amountStr = formatMoney(status.amount);
    await selection.ctx.editMessageText(
      `💰 Settlement Summary:\n\n` +
        `@${status.owingUser} owes @${status.owedUser} ${amountStr}\n\n` +
        `Are you sure you want to settle all transactions between you and @${otherUser}? ` +
        `This will erase all transaction history between you.`,
      {
        reply_markup: InlineKeyboard.from([
          [
            InlineKeyboard.text('✅ Yes, settle', `${CONFIRM_PREFIX}YES`),
            InlineKeyboard.text('❌ No, cancel', `${CONFIRM_PREFIX}NO`),
          ],
        ]),
      },
    );

    const confirmation = await waitForSelection(conversation, CONFIRM_PREFIX);
    if (confirmation.value !== 'YES') {
      await confirmation.ctx.editMessageText('Settlement cancelled.');
      return;
    }

    let settled = 0;
    try {
      settled = await conversation.external(() => settleBetween(env.DB, me, otherUser));
    } catch (error) {
      console.error({ message: 'settle failed', error: String(error) });
      await confirmation.ctx.editMessageText(
        `❌ Error: ${error instanceof Error ? error.message : String(error)}`,
      );
      return;
    }

    if (settled === 0) {
      await confirmation.ctx.editMessageText(
        `No transactions were found to settle between ${me} and ${otherUser}`,
      );
      return;
    }

    await confirmation.ctx.editMessageText(
      `✅ Settlement completed!\n\n` +
        `${settled} transaction(s) totaling ${amountStr} have been settled ` +
        `between you and @${otherUser}.`,
    );
    await trySend(
      confirmation.ctx.api,
      otherChatId,
      `✅ Settlement completed!\n\n` +
        `@${me} has settled ${settled} transaction(s) totaling ${amountStr} ` +
        `between you. All transaction history has been cleared.`,
    );
  };
}
