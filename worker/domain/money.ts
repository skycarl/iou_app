/**
 * Amounts are stored as REAL (matching the legacy float behaviour) and only
 * rounded for display or when a split share is computed.
 *
 * Python's round() and format() break exact ties to even. JS Math.round and
 * toFixed break them away from zero, which would make e.g. a $0.50 split
 * between 4 people disagree with the legacy backend. round2 reproduces the
 * Python behaviour.
 */
export function round2(value: number): number {
  const scaled = value * 100;
  const fraction = Math.abs(scaled % 1);
  if (fraction === 0.5) {
    const floor = Math.floor(scaled);
    return (floor % 2 === 0 ? floor : floor + 1) / 100;
  }
  return Math.round(scaled) / 100;
}

/** Python `f"{value:,.2f}"` -> "1,234.50" */
export function formatAmount(value: number): string {
  return round2(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Python `f"${value:,.2f}"` -> "$1,234.50" */
export function formatMoney(value: number): string {
  return `$${formatAmount(value)}`;
}

/** Python `f"${value:.2f}"` -> "$1234.50" (no thousands separator) */
export function formatMoneyPlain(value: number): string {
  return `$${round2(value).toFixed(2)}`;
}
