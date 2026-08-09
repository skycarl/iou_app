import { formatMoney } from './money.js';

/** Telegram's per-message character limit. */
export const MAX_MESSAGE_LENGTH = 4096;

export function chunkText(text: string, size = MAX_MESSAGE_LENGTH): string[] {
  if (text.length <= size) return [text];
  const chunks: string[] = [];
  for (let i = 0; i < text.length; i += size) {
    chunks.push(text.slice(i, i + size));
  }
  return chunks;
}

export function chunkButtons<T>(buttons: readonly T[], size = 3): T[][] {
  const rows: T[][] = [];
  for (let i = 0; i < buttons.length; i += size) {
    rows.push(buttons.slice(i, i + size));
  }
  return rows;
}

export interface TransactionEntry {
  sender: string;
  recipient: string;
  amount: number;
  description: string | null;
  created_at: string;
}

/** 'YYYY-MM-DD HH:MM:SS' -> 'YYYY-MM-DD', matching TransactionEntry.formatted_date. */
function formattedDate(createdAt: string): string {
  if (!createdAt) return '';
  return createdAt.slice(0, 10);
}

/** Port of `format_transactions` in bot/main.py. */
export function formatTransactions(
  entries: readonly TransactionEntry[],
  currentUser: string,
): string {
  if (entries.length === 0) return 'No transactions found.';

  const sorted = [...entries].sort((a, b) => a.created_at.localeCompare(b.created_at));
  let result = '📋 Your Transaction History:\n\n';

  sorted.forEach((entry, index) => {
    const line =
      entry.sender === currentUser
        ? `➖ You owe @${entry.recipient} ${formatMoney(entry.amount)}`
        : `➕ @${entry.sender} owes you ${formatMoney(entry.amount)}`;

    result += `${index + 1}. ${line}\n`;
    if (entry.description) result += `   📝 ${entry.description}\n`;
    const date = formattedDate(entry.created_at);
    if (date) result += `   📅 ${date}\n`;
    result += '\n';
  });

  return result;
}
