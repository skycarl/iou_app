/**
 * Amount parsing, kept bug-compatible with the Python backend this replaced so
 * the same input keeps producing the same stored value:
 *   - any alphabetic character anywhere -> reject; this is what blocks "inf",
 *     "nan" and "1e5", which would otherwise parse as numbers
 *   - keep only digits, '.' and '-'; drop the rest ("$1,234.50" -> "1234.50")
 *   - reject whatever is left if it is not a number ("12.34.56")
 *   - reject non-positive amounts
 */
export class AmountError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AmountError';
  }
}

const LETTER = /\p{L}/u;
const DIGIT = /\p{Nd}/u;

export function validateAmountStr(amount: string): number {
  if (LETTER.test(amount)) {
    throw new AmountError(`Amount "${amount}" contains invalid characters`);
  }

  let cleaned = '';
  for (const c of amount) {
    if (DIGIT.test(c) || c === '.' || c === '-') cleaned += c;
  }

  // Number('') is 0 in JS but float('') raises in Python, so guard explicitly.
  const value = cleaned === '' ? Number.NaN : Number(cleaned);
  if (!Number.isFinite(value)) {
    throw new AmountError(`Unable to parse amount "${amount}"`);
  }
  if (value <= 0) {
    throw new AmountError(`Amount must be positive (got "${amount}")`);
  }
  return value;
}
