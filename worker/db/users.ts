export interface UserRow {
  username: string;
  conversation_id: string | null;
  telegram_user_id: number | null;
}

export async function listUsers(db: D1Database): Promise<UserRow[]> {
  const { results } = await db
    .prepare('SELECT username, conversation_id, telegram_user_id FROM users ORDER BY username')
    .all<UserRow>();
  return results;
}

export async function getUserByUsername(
  db: D1Database,
  username: string,
): Promise<UserRow | null> {
  return db
    .prepare(
      'SELECT username, conversation_id, telegram_user_id FROM users WHERE username = ?',
    )
    .bind(username)
    .first<UserRow>();
}

export async function getUserByTelegramId(
  db: D1Database,
  telegramUserId: number,
): Promise<UserRow | null> {
  return db
    .prepare(
      'SELECT username, conversation_id, telegram_user_id FROM users WHERE telegram_user_id = ?',
    )
    .bind(telegramUserId)
    .first<UserRow>();
}

export async function setConversationId(
  db: D1Database,
  username: string,
  conversationId: string,
): Promise<void> {
  await db
    .prepare('UPDATE users SET conversation_id = ? WHERE username = ?')
    .bind(conversationId, username)
    .run();
}

/**
 * Backfills the Telegram numeric id for a row that does not have one yet.
 * Guarded on `telegram_user_id IS NULL` so a re-used id can never silently
 * overwrite an existing binding, and on the id not already being claimed.
 */
export async function backfillTelegramUserId(
  db: D1Database,
  username: string,
  telegramUserId: number,
): Promise<void> {
  await db
    .prepare(
      `UPDATE users SET telegram_user_id = ?
       WHERE username = ?
         AND telegram_user_id IS NULL
         AND NOT EXISTS (SELECT 1 FROM users WHERE telegram_user_id = ?)`,
    )
    .bind(telegramUserId, username, telegramUserId)
    .run();
}

/** A user can only be messaged once they have run /start. */
export function isRegistered(
  user: UserRow | null,
): user is UserRow & { conversation_id: string } {
  return user !== null && user.conversation_id !== null && user.conversation_id !== '';
}
