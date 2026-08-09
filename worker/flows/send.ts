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

export const SEND_CONVERSATION = 'send';
const PREFIX = 'SEND_RECIPIENT_';

/** /send — I hand someone an IOU: entry sender = me, recipient = them. */
export function sendFlow(env: Env) {
  return async function sendConversation(
    conversation: IouConversation,
    ctx: ConversationContext,
  ): Promise<void> {
    const me = ctx.from?.username;
    const chatId = ctx.chatId;
    if (me === undefined || chatId === undefined) return;

    const candidates = await conversation.external(() => listUsernames(env.DB, me));
    if (candidates.length === 0) {
      await ctx.reply('There is nobody else to send to.');
      return;
    }

    const prompt = await ctx.reply('Select a recipient:', {
      reply_markup: usernameKeyboard(candidates, PREFIX, 3),
    });

    const selection = await waitForSelection(conversation, PREFIX);
    const recipient = selection.value;

    const recipientChatId = await conversation.external(() =>
      conversationIdFor(env.DB, recipient),
    );
    if (recipientChatId === null) {
      await selection.ctx.api.sendMessage(chatId, notRegistered(recipient, 'Recipient'));
      return;
    }

    await selection.ctx.api.editMessageText(
      chatId,
      prompt.message_id,
      `----- Initiating send -----\nRecipient: @${recipient}\n\nEnter the amount you want to send:`,
    );

    const amount = await askAmount(conversation);
    await amount.ctx.api.editMessageText(
      chatId,
      prompt.message_id,
      `----- Initiating send -----\nRecipient: @${recipient}\n` +
        `Amount: ${amount.raw}\n\nEnter a description:`,
    );

    const { ctx: last, text: description } = await waitForText(conversation);
    const amountStr = formatMoney(amount.value);

    try {
      await conversation.external(() =>
        addEntry(env.DB, {
          conversationId: String(chatId),
          sender: me,
          recipient,
          amount: amount.value,
          description,
        }),
      );
    } catch (error) {
      console.error({ message: 'send failed', error: String(error) });
      await last.reply(errorText(error, '/send'));
      return;
    }

    await last.api.editMessageText(
      chatId,
      prompt.message_id,
      `----- Initiated send -----\nRecipient: @${recipient}\n` +
        `Amount: ${amountStr}\nDescription: ${description}`,
    );
    await last.api.sendMessage(
      chatId,
      `✅ You sent @${recipient} ${amountStr} for ${description}`,
    );
    await trySend(
      last.api,
      recipientChatId,
      `@${me} sent you ${amountStr} for ${description}`,
    );
  };
}
