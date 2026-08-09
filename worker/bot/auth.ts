import type { MiddlewareFn } from 'grammy';
import { backfillTelegramUserId, getUserByTelegramId, getUserByUsername } from '../db/users.js';
import type { BotContext, Env } from '../types.js';
import { GENERIC_ERROR, NO_USERNAME, UNAUTHORIZED, UNAUTHORIZED_CALLBACK } from './strings.js';

async function refuse(ctx: BotContext, text: string, callbackText: string): Promise<void> {
  if (ctx.callbackQuery !== undefined) {
    await ctx.answerCallbackQuery({ text: callbackText, show_alert: true });
    return;
  }
  if (ctx.chat !== undefined) {
    await ctx.reply(text);
  }
}

/**
 * Gates every update on the `users` allowlist. There is no self-signup: rows
 * are added to D1 by hand. Fails closed — a database error refuses the update
 * rather than letting it through.
 */
export function authorize(env: Env): MiddlewareFn<BotContext> {
  return async (ctx, next) => {
    const from = ctx.from;
    if (from === undefined) return;
    if (from.is_bot) return;

    let user = null;
    try {
      // The numeric id is stable across username changes, so prefer it.
      user = await getUserByTelegramId(env.DB, from.id);
      if (user === null && from.username !== undefined) {
        const byName = await getUserByUsername(env.DB, from.username);
        if (byName !== null && byName.telegram_user_id === null) {
          // First sighting of an allowlisted account: bind the numeric id so a
          // later username change cannot lock them out, and so nobody who
          // renames themselves into this username can take it over.
          await backfillTelegramUserId(env.DB, byName.username, from.id);
          user = { ...byName, telegram_user_id: from.id };
        }
      }
    } catch (error) {
      console.error({ message: 'authorization lookup failed', error: String(error) });
      await refuse(ctx, GENERIC_ERROR, GENERIC_ERROR);
      return;
    }

    if (user === null) {
      const text = from.username === undefined ? NO_USERNAME : UNAUTHORIZED;
      await refuse(ctx, text, UNAUTHORIZED_CALLBACK);
      return;
    }

    ctx.iouUser = user;
    await next();
  };
}
