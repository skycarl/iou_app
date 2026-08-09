import type { Context } from 'grammy';
import type { Conversation, ConversationFlavor } from '@grammyjs/conversations';
import type { UserRow } from './db/users.js';

export interface Env {
  DB: D1Database;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_WEBHOOK_SECRET: string;
}

/** Set by the authorization middleware before any handler runs. */
export interface IouFlavor {
  iouUser: UserRow;
}

/** Context in the outer middleware tree. */
export type BotContext = ConversationFlavor<Context & IouFlavor>;

/**
 * Context inside a conversation. The conversations plugin builds these from
 * scratch on every replay, so they carry no properties added by the outer
 * middleware — flows read the database through `conversation.external` instead.
 */
export type ConversationContext = Context;

export type IouConversation = Conversation<BotContext, ConversationContext>;
