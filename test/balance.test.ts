import { describe, expect, it } from 'vitest';
import { computeIouStatus } from '../worker/domain/balance.js';

const entry = (sender: string, recipient: string, amount: number) => ({
  sender,
  recipient,
  amount,
});

describe('computeIouStatus', () => {
  it('reports a zero balance in the queried order when there is nothing outstanding', () => {
    expect(computeIouStatus([], 'alice', 'bob')).toEqual({
      owingUser: 'alice',
      owedUser: 'bob',
      amount: 0,
    });
  });

  it('nets entries in both directions', () => {
    const entries = [
      entry('alice', 'bob', 30),
      entry('alice', 'bob', 12.5),
      entry('bob', 'alice', 10),
    ];
    expect(computeIouStatus(entries, 'alice', 'bob')).toEqual({
      owingUser: 'alice',
      owedUser: 'bob',
      amount: 32.5,
    });
  });

  it('flips the direction when the net is negative', () => {
    const entries = [entry('alice', 'bob', 5), entry('bob', 'alice', 20)];
    expect(computeIouStatus(entries, 'alice', 'bob')).toEqual({
      owingUser: 'bob',
      owedUser: 'alice',
      amount: 15,
    });
  });

  it('is symmetric under swapping the two users', () => {
    const entries = [entry('alice', 'bob', 5), entry('bob', 'alice', 20)];
    expect(computeIouStatus(entries, 'bob', 'alice')).toEqual({
      owingUser: 'bob',
      owedUser: 'alice',
      amount: 15,
    });
  });

  it('reports an exactly cancelled balance as zero', () => {
    const entries = [entry('alice', 'bob', 40), entry('bob', 'alice', 40)];
    expect(computeIouStatus(entries, 'alice', 'bob').amount).toBe(0);
  });

  it('ignores entries involving other people', () => {
    const entries = [
      entry('alice', 'bob', 10),
      entry('alice', 'carol', 999),
      entry('carol', 'bob', 999),
    ];
    expect(computeIouStatus(entries, 'alice', 'bob').amount).toBe(10);
  });

  it('rounds float tails to 2dp for display without touching the stored values', () => {
    const entries = [
      entry('alice', 'bob', 3.3333333333333335),
      entry('alice', 'bob', 3.3333333333333335),
      entry('alice', 'bob', 3.3333333333333335),
    ];
    expect(computeIouStatus(entries, 'alice', 'bob').amount).toBe(10);
  });
});
