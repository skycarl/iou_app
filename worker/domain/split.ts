import { formatMoneyPlain, round2 } from './money.js';

export class SplitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SplitError';
  }
}

export interface SplitEntry {
  sender: string;
  recipient: string;
  amount: number;
  description: string;
}

export interface SplitResult {
  evenShare: number;
  entries: SplitEntry[];
}

/**
 * Port of the `/split` endpoint (app/iou/views.py:162-204).
 *
 * The payer counts towards the divisor whenever they appear in `participants`
 * (the bot always adds them), and only the other participants get an entry —
 * each of them owes the payer one even share.
 */
export function computeSplit(input: {
  payer: string;
  amount: number;
  participants: readonly string[];
  description: string;
}): SplitResult {
  const { payer, amount, participants, description } = input;

  if (participants.length < 2) {
    throw new SplitError('At least two participants are required for a split.');
  }

  const evenShare = round2(amount / participants.length);
  const participantsStr = participants.join(', ');
  const entryDescription =
    `Split: ${description} | ` +
    `Total: ${formatMoneyPlain(amount)} | ` +
    `Participants: ${participantsStr}`;

  const entries = participants
    .filter((participant) => participant !== payer)
    .map((participant) => ({
      sender: participant,
      recipient: payer,
      amount: evenShare,
      description: entryDescription,
    }));

  return { evenShare, entries };
}
