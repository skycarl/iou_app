import type { VersionedState, VersionedStateStorage } from '@grammyjs/conversations';

/**
 * Storage adapter for the conversations plugin, backed by the `sessions` table.
 * Conversation state has to outlive the request on Workers, so it cannot use
 * the plugin's default in-memory storage.
 */
export function createD1Storage<S>(db: D1Database): VersionedStateStorage<string, S> {
  return {
    async read(key: string): Promise<VersionedState<S> | undefined> {
      const row = await db
        .prepare('SELECT value FROM sessions WHERE key = ?')
        .bind(key)
        .first<{ value: string }>();
      if (row === null) return undefined;
      return JSON.parse(row.value) as VersionedState<S>;
    },

    async write(key: string, state: VersionedState<S>): Promise<void> {
      await db
        .prepare(
          `INSERT INTO sessions (key, value) VALUES (?, ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value`,
        )
        .bind(key, JSON.stringify(state))
        .run();
    },

    async delete(key: string): Promise<void> {
      await db.prepare('DELETE FROM sessions WHERE key = ?').bind(key).run();
    },
  };
}
