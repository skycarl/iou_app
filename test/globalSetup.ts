import { build } from 'esbuild';

/**
 * `@grammyjs/conversations` ships CommonJS that `require`s grammY, whose
 * Workers entry point is ESM. Wrangler's esbuild pass reconciles the two;
 * Vite's module runner does not, and every conversation throws on the
 * unresolved re-export. So the flow tests import a bundle produced the same
 * way the deployed Worker is, which also proves the real bundle works.
 */
export async function setup(): Promise<void> {
  await build({
    entryPoints: ['test/botEntry.ts'],
    outfile: 'test/generated/bot.mjs',
    bundle: true,
    format: 'esm',
    platform: 'browser',
    target: 'es2022',
    conditions: ['workerd', 'worker', 'browser'],
    external: ['cloudflare:*', 'node:*'],
    logLevel: 'warning',
  });
}
