import { env } from 'cloudflare:test';
import { beforeEach, describe, expect, it } from 'vitest';
import {
  addEntries,
  addEntry,
  getActiveEntriesBetween,
  getActiveEntriesForUser,
  settleBetween,
} from '../worker/db/entries.js';
import { computeIouStatus } from '../worker/domain/balance.js';

async function seed(sender: string, recipient: string, amount: number): Promise<void> {
  await addEntry(env.DB, {
    conversationId: '1',
    sender,
    recipient,
    amount,
    description: `${sender}->${recipient}`,
  });
}

beforeEach(async () => {
  await env.DB.prepare('DELETE FROM entries').run();
});

describe('entries in D1', () => {
  it('round-trips an entry as an active row', async () => {
    await seed('alice', 'bob', 21.5);
    const rows = await getActiveEntriesBetween(env.DB, 'alice', 'bob');
    expect(rows).toHaveLength(1);
    expect(rows[0]?.amount).toBe(21.5);
    expect(rows[0]?.deleted).toBe(0);
    expect(rows[0]?.created_at).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  });

  it('matches entries between two users in either direction', async () => {
    await seed('alice', 'bob', 10);
    await seed('bob', 'alice', 4);
    await seed('alice', 'carol', 99);

    const rows = await getActiveEntriesBetween(env.DB, 'alice', 'bob');
    expect(rows).toHaveLength(2);
    expect(computeIouStatus(rows, 'alice', 'bob')).toEqual({
      owingUser: 'alice',
      owedUser: 'bob',
      amount: 6,
    });
  });

  it('lists every entry a user is party to', async () => {
    await seed('alice', 'bob', 10);
    await seed('carol', 'alice', 5);
    await seed('bob', 'carol', 7);

    const rows = await getActiveEntriesForUser(env.DB, 'alice');
    expect(rows).toHaveLength(2);
  });

  it('writes all entries of a split together', async () => {
    await addEntries(env.DB, [
      { conversationId: '1', sender: 'bob', recipient: 'alice', amount: 20, description: 'a' },
      { conversationId: '1', sender: 'carol', recipient: 'alice', amount: 20, description: 'a' },
    ]);
    expect(await getActiveEntriesForUser(env.DB, 'alice')).toHaveLength(2);
  });

  describe('settleBetween', () => {
    it('soft-deletes every entry between the pair and reports the count', async () => {
      await seed('alice', 'bob', 10);
      await seed('bob', 'alice', 4);

      const settled = await settleBetween(env.DB, 'alice', 'bob');
      expect(settled).toBe(2);
      expect(await getActiveEntriesBetween(env.DB, 'alice', 'bob')).toHaveLength(0);
    });

    it('keeps the history rather than deleting rows', async () => {
      await seed('alice', 'bob', 10);
      await settleBetween(env.DB, 'alice', 'bob');

      const row = await env.DB.prepare(
        'SELECT deleted, deleted_at FROM entries WHERE sender = ?',
      )
        .bind('alice')
        .first<{ deleted: number; deleted_at: string | null }>();
      expect(row?.deleted).toBe(1);
      expect(row?.deleted_at).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    });

    it('leaves other people’s entries untouched', async () => {
      await seed('alice', 'bob', 10);
      await seed('alice', 'carol', 10);

      expect(await settleBetween(env.DB, 'alice', 'bob')).toBe(1);
      expect(await getActiveEntriesBetween(env.DB, 'alice', 'carol')).toHaveLength(1);
    });

    it('settles nothing the second time around', async () => {
      await seed('alice', 'bob', 10);
      expect(await settleBetween(env.DB, 'alice', 'bob')).toBe(1);
      expect(await settleBetween(env.DB, 'alice', 'bob')).toBe(0);
    });

    it('zeroes the balance', async () => {
      await seed('alice', 'bob', 10);
      await seed('bob', 'alice', 4);
      await settleBetween(env.DB, 'alice', 'bob');

      const rows = await getActiveEntriesBetween(env.DB, 'alice', 'bob');
      expect(computeIouStatus(rows, 'alice', 'bob').amount).toBe(0);
    });
  });
});
