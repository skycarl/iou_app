import { defineConfig } from 'vitest/config';
import { cloudflareTest, readD1Migrations } from '@cloudflare/vitest-pool-workers';

// Read in Node so the tests, which run inside workerd, can apply the real
// migration files rather than a hand-copied schema that could drift.
const migrations = await readD1Migrations('./migrations');

export default defineConfig({
  plugins: [
    cloudflareTest({
      miniflare: {
        compatibilityDate: '2026-08-08',
        compatibilityFlags: ['nodejs_compat'],
        d1Databases: ['DB'],
        bindings: {
          TELEGRAM_BOT_TOKEN: '123456:test-token',
          TELEGRAM_WEBHOOK_SECRET: 'correct-webhook-secret',
          TEST_MIGRATIONS: migrations,
        },
      },
    }),
  ],
  test: {
    globalSetup: ['./test/globalSetup.ts'],
    setupFiles: ['./test/setup.ts'],
  },
});
