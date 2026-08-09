/**
 * Port of `validate_amount_str` from app/iou/schema.py.
 *
 * Python semantics being reproduced:
 *   - any alphabetic character anywhere -> reject (this is what blocks "inf",
 *     "nan" and "1e5" from reaching float())
 *   - keep only digits, '.' and '-'; drop everything else ("$1,234.50" -> "1234.50")
 *   - float() on the remainder; failure -> reject ("12.34.56" -> reject)
 *   - non-positive -> reject
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
