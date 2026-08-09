/**
 * User-facing text. The phrasing is inherited from the Python bot this
 * replaced, so the bot still reads the same to the people already using it.
 */

export const UNAUTHORIZED = 'Sorry, you are not authorized to use this bot.';
export const UNAUTHORIZED_CALLBACK = 'Unauthorized access!';
export const NO_USERNAME = 'You must have a Telegram username to use this bot.';
export const ALREADY_REGISTERED = 'You are already registered.';
export const REGISTRATION_SUCCESSFUL = 'Registration successful!';
export const GENERIC_ERROR = 'An error occurred. Please try again later.';
export const CANCELLED = 'Cancelled.';
export const NOTHING_TO_CANCEL = 'There is nothing to cancel.';
export const HELLO = 'Hello to yourself!';

export const HELP = [
  'To send money: /send (inline guided flow)',
  'To bill someone: /bill (inline guided flow)',
  'To check IOU status: /query (inline guided flow)',
  'To split a bill among multiple participants: /split (inline guided flow)',
  'To settle all transactions with another user: /settle (inline guided flow)',
  'To list your transactions: /list',
  'To abandon a guided flow: /cancel',
].join('\n\n');

export function notRegistered(username: string, role = 'User'): string {
  return `${role} @${username} is not registered. They need to /start the bot first.`;
}
