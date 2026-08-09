import pkg from '../package.json' with { type: 'json' };

/** Inlined at bundle time so /version needs no network or filesystem access. */
export const VERSION: string = pkg.version;
