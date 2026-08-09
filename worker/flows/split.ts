import { InlineKeyboard } from 'grammy';
import { addEntries } from '../db/entries.js';
import { chunkButtons } from '../domain/format.js';
import { formatMoney } from '../domain/money.js';
import { computeSplit } from '../domain/split.js';
import {
  askAmount,
  conversationIdFor,
  conversationIdsFor,
  errorText,
  listUsernames,
  trySend,
  usernameKeyboard,
  waitForSelection,
  waitForText,
} from '../bot/helpers.js';
import { notRegistered } from '../bot/strings.js';
import type { ConversationContext, Env, IouConversation } from '../types.js';

export const SPLIT_CONVERSATION = 'split';
const PAYER_PREFIX = 'SPLIT_PAYER_';
const PARTICIPANT_PREFIX = 'SPLIT_PART_';
const TOGGLE = 'TOGGLE_';
const DONE = 'DONE';

function participantsKeyboard(
  everyone: readonly string[],
  selected: ReadonlySet<string>,
): InlineKeyboard {
  const rows = chunkButtons(everyone, everyone.length).map((row) =>
    row.map((username) =>
      InlineKeyboard.text(
        `${selected.has(username) ? '✅' : '⬜'} ${username}`,
        `${PARTICIPANT_PREFIX}${TOGGLE}${username}`,
      ),
    ),
  );
  rows.push([InlineKeyboard.text('Done', `${PARTICIPANT_PREFIX}${DONE}`)]);
  return InlineKeyboard.from(rows);
}

function participantsPrompt(selected: ReadonlySet<string>): string {
  const list = [...selected].map((username) => `@${username}`).join(', ');
  return `Select participants (toggle by tapping). Currently selected:\n${list === '' ? '(none)' : list}`;
}

/** /split — divide an amount evenly; everyone but the payer owes the payer a share. */
export function splitFlow(env: Env) {
  return async function splitConversation(
    conversation: IouConversation,
    ctx: ConversationContext,
  ): Promise<void> {
    const me = ctx.from?.username;
    const chatId = ctx.chatId;
    if (me === undefined || chatId === undefined) return;

    const everyone = await conversation.external(() => listUsernames(env.DB));
    if (everyone.length < 2) {
      await ctx.reply('There are not enough users to split with.');
      return;
    }

    const prompt = await ctx.reply('Select who paid the bill:', {
      reply_markup: usernameKeyboard(everyone, PAYER_PREFIX, everyone.length),
    });

    const payerSelection = await waitForSelection(conversation, PAYER_PREFIX);
    const payer = payerSelection.value;

    const payerChatId = await conversation.external(() => conversationIdFor(env.DB, payer));
    if (payerChatId === null) {
      await payerSelection.ctx.api.sendMessage(chatId, notRegistered(payer, 'Payer'));
      return;
    }

    await payerSelection.ctx.api.editMessageText(
      chatId,
      prompt.message_id,
      `----- Initiating split -----\nPayer: @${payer}\n\nEnter the amount:`,
    );

    const amount = await askAmount(conversation);
    await amount.ctx.api.editMessageText(
      chatId,
      prompt.message_id,
      `----- Initiating split -----\nPayer: @${payer}\n` +
        `Amount: ${amount.raw}\n\nEnter a description:`,
    );

    const { ctx: describeCtx, text: description } = await waitForText(conversation);

    // The initiator and the payer always start selected, as in the legacy bot.
    const selected = new Set<string>([me, payer]);
    const picker = await describeCtx.reply(participantsPrompt(selected), {
      reply_markup: participantsKeyboard(everyone, selected),
    });

    let doneCtx: ConversationContext;
    for (;;) {
      const action = await waitForSelection(conversation, PARTICIPANT_PREFIX);
      if (action.value === DONE) {
        doneCtx = action.ctx;
        break;
      }

      const username = action.value.slice(TOGGLE.length);
      if (!everyone.includes(username)) continue;

      const registered = await conversation.external(() => conversationIdFor(env.DB, username));
      if (registered === null) {
        await action.ctx.api.sendMessage(chatId, notRegistered(username));
        continue;
      }

      if (username === payer && selected.has(username)) {
        await action.ctx.api.sendMessage(
          chatId,
          `The payer @${payer} cannot be removed from the split.`,
        );
        continue;
      }

      if (selected.has(username)) {
        selected.delete(username);
        if (username === me) {
          await action.ctx.api.sendMessage(
            chatId,
            "Heads up: You've removed yourself from the split. Did you mean to do that? " +
              'You can re-select yourself if this was accidental.',
          );
        }
      } else {
        selected.add(username);
      }

      await action.ctx.api.editMessageText(
        chatId,
        picker.message_id,
        participantsPrompt(selected),
        { reply_markup: participantsKeyboard(everyone, selected) },
      );
    }

    // Canonical ordering keeps the stored description stable run to run.
    const participants = everyone.filter((username) => selected.has(username));

    const chatIds = await conversation.external(() => conversationIdsFor(env.DB, participants));
    const unregistered = participants.filter((username) => chatIds[username] === null);
    if (unregistered.length > 0) {
      await doneCtx.editMessageText(
        'The following users are not registered: ' +
          unregistered.map((username) => `@${username}`).join(', ') +
          '. They need to /start the bot first.',
      );
      return;
    }

    try {
      const result = computeSplit({
        payer,
        amount: amount.value,
        participants,
        description,
      });

      await conversation.external(() =>
        addEntries(
          env.DB,
          result.entries.map((entry) => ({
            conversationId: String(chatId),
            sender: entry.sender,
            recipient: entry.recipient,
            amount: entry.amount,
            description: entry.description,
          })),
        ),
      );

      const amountStr = formatMoney(amount.value);
      const shareStr = formatMoney(result.evenShare);
      const participantsText = participants.map((username) => `@${username}`).join(', ');

      await doneCtx.api.editMessageText(
        chatId,
        prompt.message_id,
        `----- Initiated split -----\nPayer: @${payer}\n` +
          `Amount: ${amountStr}\nDescription: ${description}\n` +
          `Participants: ${participantsText}`,
      );
      await doneCtx.editMessageText('✅ Split successful!');

      const notification =
        `💳 @${me} split a transaction!\n` +
        `Payer: @${payer}\n` +
        `Total amount: ${amountStr}\n` +
        `Split portion: ${shareStr}\n` +
        `Description: ${description}\n` +
        `Participants: ${participantsText}`;

      for (const username of participants) {
        const target = chatIds[username];
        if (target !== null && target !== undefined) {
          await trySend(doneCtx.api, target, notification);
        }
      }
    } catch (error) {
      console.error({ message: 'split failed', error: String(error) });
      await doneCtx.editMessageText(errorText(error, '/split'));
    }
  };
}
