import { round2 } from './money.js';

export interface BalanceEntry {
  sender: string;
  recipient: string;
  amount: number;
}

export interface IouStatus {
  owingUser: string;
  owedUser: string;
  /** Always non-negative, rounded to 2dp for display. */
  amount: number;
}

/**
 * Nets out what two users owe each other. A sender owes their recipient.
 *
 * `entries` must already exclude soft-deleted rows. Entries not between these
 * two users are ignored, so a caller may pass a wider set.
 */
export function computeIouStatus(
  entries: readonly BalanceEntry[],
  user1: string,
  user2: string,
): IouStatus {
  let totalUser1Owes = 0;
  let totalUser2Owes = 0;

  for (const entry of entries) {
    if (entry.sender === user1 && entry.recipient === user2) {
      totalUser1Owes += entry.amount;
    } else if (entry.sender === user2 && entry.recipient === user1) {
      totalUser2Owes += entry.amount;
    }
  }

  const difference = totalUser1Owes - totalUser2Owes;

  if (difference >= 0) {
    return { owingUser: user1, owedUser: user2, amount: round2(difference) };
  }
  return { owingUser: user2, owedUser: user1, amount: round2(Math.abs(difference)) };
}
