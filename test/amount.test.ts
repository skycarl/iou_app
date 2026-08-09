import { describe, expect, it } from 'vitest';
import { AmountError, validateAmountStr } from '../worker/domain/amount.js';
import { formatMoney, formatMoneyPlain, round2 } from '../worker/domain/money.js';

describe('validateAmountStr', () => {
  it('accepts plain decimals', () => {
    expect(validateAmountStr('21.5')).toBe(21.5);
    expect(validateAmountStr('7')).toBe(7);
    expect(validateAmountStr('.5')).toBe(0.5);
    expect(validateAmountStr('1.')).toBe(1);
  });

  it('strips currency symbols and thousands separators', () => {
    expect(validateAmountStr('$1,234.50')).toBe(1234.5);
    expect(validateAmountStr('  $42  ')).toBe(42);
    expect(validateAmountStr('+5')).toBe(5);
  });

  it('rejects anything containing letters', () => {
    for (const input of ['12abc', 'abc', 'ten', '1e5', 'inf', 'nan', '5 USD']) {
      expect(() => validateAmountStr(input)).toThrow(AmountError);
    }
    expect(() => validateAmountStr('12abc')).toThrow(/contains invalid characters/);
  });

  it('rejects unparseable numbers', () => {
    for (const input of ['12.34.56', '1-2', '--1', '.', '-', '', '$', ',,,']) {
      expect(() => validateAmountStr(input)).toThrow(AmountError);
    }
    expect(() => validateAmountStr('12.34.56')).toThrow(/Unable to parse amount/);
  });

  it('rejects non-positive amounts', () => {
    for (const input of ['0', '0.00', '-5', '-0.01']) {
      expect(() => validateAmountStr(input)).toThrow(/must be positive/);
    }
  });
});

describe('money formatting', () => {
  it('breaks exact ties to even, like Python round()', () => {
    expect(round2(0.125)).toBe(0.12);
    expect(round2(0.135)).toBe(0.14);
    // 1.005 is below the tie in binary, so Python rounds it down too.
    expect(round2(1.005)).toBe(1);
  });

  it('renders amounts the way the legacy bot did', () => {
    expect(formatMoney(1234.5)).toBe('$1,234.50');
    expect(formatMoney(7)).toBe('$7.00');
    expect(formatMoney(3.3333333333333335)).toBe('$3.33');
    expect(formatMoneyPlain(1234.5)).toBe('$1234.50');
  });
});
