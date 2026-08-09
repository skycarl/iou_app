import { addEntry } from '../db/entries.js';
import { formatMoney } from '../domain/money.js';
import {
  askAmount,
  conversationIdFor,
  errorText,
  listUsernames,
  trySend,
  usernameKeyboard,
  waitForSelection,
  waitForText,
} from '../bot/helpers.js';
import { notRegistered } from '../bot/strings.js';
import type { ConversationContext, Env, IouConversation } from '../types.js';

export const BILL_CONVERSATION = 'bill';
const PREFIX = 'BILL_SENDER_';

/** /bill — someone owes me: entry sender = them, recipient = me. */
export function billFlow(env: Env) {
  return async function billConversation(
    conversation: IouConversation,
    ctx: ConversationContext,
  ): Promise<void> {
    const me = ctx.from?.username;
    const chatId = ctx.chatId;
    if (me === undefined || chatId === undefined) return;

    const candidates = await conversation.external(() => listUsernames(env.DB, me));
    if (candidates.length === 0) {
      await ctx.reply('There is nobody else to bill.');
      return;
    }

    const prompt = await ctx.reply('Select the user who owes you:', {
      reply_markup: usernameKeyboard(candidates, PREFIX, 3),
    });

    const selection = await waitForSelection(conversation, PREFIX);
    const sender = selection.value;

    const senderChatId = await conversation.external(() => conversationIdFor(env.DB, sender));
    if (senderChatId === null) {
      await selection.ctx.api.sendMessage(chatId, notRegistered(sender));
      return;
    }

    await selection.ctx.api.editMessageText(
      chatId,
      prompt.message_id,
      `----- Initiating bill -----\nUser: @${sender}\n\nEnter the amount you want to bill:`,
    );

    const amount = await askAmount(conversation);
    await amount.ctx.api.editMessageText(
      chatId,
      prompt.message_id,
      `----- Initiating bill -----\nUser: @${sender}\n` +
        `Amount: ${amount.raw}\n\nEnter a description:`,
    );

    const { ctx: last, text: description } = await waitForText(conversation);
    const amountStr = formatMoney(amount.value);

    try {
      await conversation.external(() =>
        addEntry(env.DB, {
          conversationId: String(chatId),
          sender,
          recipient: me,
          amount: amount.value,
          description,
        }),
      );
    } catch (error) {
      console.error({ message: 'bill failed', error: String(error) });
      await last.reply(errorText(error, '/bill'));
      return;
    }

    await last.api.editMessageText(
      chatId,
      prompt.message_id,
      `----- Initiated bill -----\nUser: @${sender}\n` +
        `Amount: ${amountStr}\nDescription: ${description}`,
    );
    await last.api.sendMessage(
      chatId,
      `✅ You have billed @${sender} ${amountStr} for ${description}`,
    );
    await trySend(
      last.api,
      senderChatId,
      `@${me} billed you ${amountStr} for ${description}`,
    );
  };
}
