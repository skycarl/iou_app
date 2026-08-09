import { describe, expect, it } from 'vitest';
import { SplitError, computeSplit } from '../worker/domain/split.js';

describe('computeSplit', () => {
  it('counts the payer in the divisor but gives them no entry', () => {
    const result = computeSplit({
      payer: 'alice',
      amount: 60,
      participants: ['alice', 'bob', 'carol'],
      description: 'dinner',
    });

    expect(result.evenShare).toBe(20);
    expect(result.entries).toHaveLength(2);
    expect(result.entries.map((e) => e.sender)).toEqual(['bob', 'carol']);
    expect(result.entries.every((e) => e.recipient === 'alice')).toBe(true);
    expect(result.entries.every((e) => e.amount === 20)).toBe(true);
  });

  it('has every participant owe the payer, so the payer is owed share × (n-1)', () => {
    const result = computeSplit({
      payer: 'alice',
      amount: 100,
      participants: ['alice', 'bob', 'carol', 'dave'],
      description: 'tickets',
    });
    const owedToPayer = result.entries.reduce((sum, e) => sum + e.amount, 0);
    expect(result.evenShare).toBe(25);
    expect(owedToPayer).toBe(75);
  });

  it('rounds the share to 2dp, matching the legacy backend', () => {
    const result = computeSplit({
      payer: 'alice',
      amount: 10,
      participants: ['alice', 'bob', 'carol'],
      description: 'coffee',
    });
    expect(result.evenShare).toBe(3.33);
  });

  it('embeds the total and participants in each entry description', () => {
    const result = computeSplit({
      payer: 'alice',
      amount: 1234.5,
      participants: ['alice', 'bob'],
      description: 'hotel',
    });
    expect(result.entries[0]?.description).toBe(
      'Split: hotel | Total: $1234.50 | Participants: alice, bob',
    );
  });

  it('still divides by the participant count when the payer is not a participant', () => {
    const result = computeSplit({
      payer: 'alice',
      amount: 30,
      participants: ['bob', 'carol'],
      description: 'gift',
    });
    expect(result.evenShare).toBe(15);
    expect(result.entries).toHaveLength(2);
  });

  it('refuses a split with fewer than two participants', () => {
    expect(() =>
      computeSplit({ payer: 'alice', amount: 10, participants: ['alice'], description: 'x' }),
    ).toThrow(SplitError);
    expect(() =>
      computeSplit({ payer: 'alice', amount: 10, participants: ['alice'], description: 'x' }),
    ).toThrow('At least two participants are required for a split.');
  });
});
