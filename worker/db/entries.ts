export interface EntryRow {
  id: string;
  created_at: string;
  conversation_id: string | null;
  sender: string;
  recipient: string;
  amount: number;
  description: string | null;
  deleted: number;
  deleted_at: string | null;
}

export interface NewEntry {
  conversationId: string | null;
  sender: string;
  recipient: string;
  amount: number;
  description: string | null;
}

/** Legacy timestamp format, now written in UTC. */
export function nowTimestamp(): string {
  return new Date().toISOString().slice(0, 19).replace('T', ' ');
}

const INSERT_SQL = `INSERT INTO entries
  (id, created_at, conversation_id, sender, recipient, amount, description, deleted, deleted_at)
  VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)`;

function insertStatement(db: D1Database, entry: NewEntry, createdAt: string): D1PreparedStatement {
  return db
    .prepare(INSERT_SQL)
    .bind(
      crypto.randomUUID(),
      createdAt,
      entry.conversationId,
      entry.sender,
      entry.recipient,
      entry.amount,
      entry.description,
    );
}

export async function addEntry(db: D1Database, entry: NewEntry): Promise<void> {
  await insertStatement(db, entry, nowTimestamp()).run();
}

/** All entries of a split are written in one transaction so a split is all-or-nothing. */
export async function addEntries(db: D1Database, entries: readonly NewEntry[]): Promise<void> {
  if (entries.length === 0) return;
  const createdAt = nowTimestamp();
  await db.batch(entries.map((entry) => insertStatement(db, entry, createdAt)));
}

export async function getActiveEntriesBetween(
  db: D1Database,
  user1: string,
  user2: string,
): Promise<EntryRow[]> {
  const { results } = await db
    .prepare(
      `SELECT * FROM entries
       WHERE deleted = 0
         AND ((sender = ?1 AND recipient = ?2) OR (sender = ?2 AND recipient = ?1))
       ORDER BY created_at`,
    )
    .bind(user1, user2)
    .all<EntryRow>();
  return results;
}

export async function getActiveEntriesForUser(
  db: D1Database,
  username: string,
): Promise<EntryRow[]> {
  const { results } = await db
    .prepare(
      `SELECT * FROM entries
       WHERE deleted = 0 AND (sender = ?1 OR recipient = ?1)
       ORDER BY created_at`,
    )
    .bind(username)
    .all<EntryRow>();
  return results;
}

/**
 * Soft-deletes every active entry between the two users.
 *
 * A single UPDATE, so unlike the legacy per-row loop (which could stop halfway
 * and leave a partially settled balance) this either settles everything or
 * nothing. Returns the number of entries settled.
 */
export async function settleBetween(
  db: D1Database,
  user1: string,
  user2: string,
): Promise<number> {
  const result = await db
    .prepare(
      `UPDATE entries SET deleted = 1, deleted_at = ?3
       WHERE deleted = 0
         AND ((sender = ?1 AND recipient = ?2) OR (sender = ?2 AND recipient = ?1))`,
    )
    .bind(user1, user2, nowTimestamp())
    .run();
  return result.meta.changes ?? 0;
}
