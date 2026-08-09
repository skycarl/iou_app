import { InlineKeyboard } from 'grammy';
import type { Api } from 'grammy';
import { AmountError, validateAmountStr } from '../domain/amount.js';
import { chunkButtons } from '../domain/format.js';
import { getUserByUsername, isRegistered, listUsers } from '../db/users.js';
import type { ConversationContext, IouConversation } from '../types.js';
import { CANCELLED } from './strings.js';

export function usernameKeyboard(
  usernames: readonly string[],
  prefix: string,
  perRow: number,
): InlineKeyboard {
  return InlineKeyboard.from(
    chunkButtons(usernames, perRow).map((row) =>
      row.map((username) => InlineKeyboard.text(username, `${prefix}${username}`)),
    ),
  );
}

/** All authorized usernames, optionally minus the caller (legacy get_chat_members). */
export async function listUsernames(db: D1Database, exclude?: string | null): Promise<string[]> {
  const users = await listUsers(db);
  return users.map((user) => user.username).filter((username) => username !== exclude);
}

/** The chat a user can be notified in, or null if they have never run /start. */
export async function conversationIdFor(
  db: D1Database,
  username: string,
): Promise<string | null> {
  const user = await getUserByUsername(db, username);
  return isRegistered(user) ? user.conversation_id : null;
}

export async function conversationIdsFor(
  db: D1Database,
  usernames: readonly string[],
): Promise<Record<string, string | null>> {
  const users = await listUsers(db);
  const byName = new Map(users.map((user) => [user.username, user]));
  const result: Record<string, string | null> = {};
  for (const username of usernames) {
    const user = byName.get(username) ?? null;
    result[username] = isRegistered(user) ? user.conversation_id : null;
  }
  return result;
}

/**
 * Notifies a user in their own chat. Runs through the conversation-aware `api`
 * so replays do not resend it, and a delivery failure (blocked bot, stale chat
 * id) never breaks the sender's flow.
 */
export async function trySend(api: Api, chatId: string, text: string): Promise<void> {
  try {
    await api.sendMessage(Number(chatId), text);
  } catch (error) {
    console.error({ message: 'notification failed', chatId, error: String(error) });
  }
}

interface CallbackSelection {
  ctx: ConversationContext;
  value: string;
}

function isCancel(ctx: ConversationContext): boolean {
  return ctx.message?.text?.trim() === '/cancel';
}

/**
 * Waits for a callback query whose data starts with `prefix`, ignoring anything
 * else, and treats /cancel as an abort. `conversation.halt()` never returns.
 */
export async function waitForSelection(
  conversation: IouConversation,
  prefix: string,
): Promise<CallbackSelection> {
  for (;;) {
    const ctx = await conversation.wait();
    if (isCancel(ctx)) {
      await ctx.reply(CANCELLED);
      await conversation.halt();
    }
    const data = ctx.callbackQuery?.data;
    if (data === undefined) continue;
    await ctx.answerCallbackQuery();
    if (data.startsWith(prefix)) {
      return { ctx, value: data.slice(prefix.length) };
    }
  }
}

/** Waits for a plain text message, treating /cancel as an abort. */
export async function waitForText(
  conversation: IouConversation,
): Promise<{ ctx: ConversationContext; text: string }> {
  for (;;) {
    const ctx = await conversation.wait();
    if (isCancel(ctx)) {
      await ctx.reply(CANCELLED);
      await conversation.halt();
    }
    if (ctx.callbackQuery !== undefined) {
      await ctx.answerCallbackQuery();
      continue;
    }
    const text = ctx.message?.text?.trim();
    if (text === undefined || text === '') continue;
    if (text.startsWith('/')) {
      await ctx.reply('Please answer the question above, or /cancel to start over.');
      continue;
    }
    return { ctx, text };
  }
}

/**
 * Asks until a parseable, positive amount arrives. The legacy bot only
 * validated after the description step and then dropped the whole flow; this
 * reprompts instead.
 */
export async function askAmount(
  conversation: IouConversation,
): Promise<{ ctx: ConversationContext; raw: string; value: number }> {
  for (;;) {
    const { ctx, text } = await waitForText(conversation);
    try {
      return { ctx, raw: text, value: validateAmountStr(text) };
    } catch (error) {
      const message = error instanceof AmountError ? error.message : 'Invalid amount.';
      await ctx.reply(`❌ Error: ${message}\n\nEnter the amount again, or /cancel.`);
    }
  }
}

/** Renders a user-facing error line, matching the legacy "❌ Error: …" phrasing. */
export function errorText(error: unknown, retryCommand: string): string {
  const message = error instanceof Error ? error.message : String(error);
  return `❌ Error: ${message}\n\nTap here to try again: ${retryCommand}`;
}
