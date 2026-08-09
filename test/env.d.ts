import type { D1Migration } from '@cloudflare/vitest-pool-workers';
import type { Env as WorkerEnv } from '../worker/types.js';

declare global {
  namespace Cloudflare {
    interface Env extends WorkerEnv {
      /** Migrations read in Node by vitest.config.ts and applied in test/setup.ts. */
      TEST_MIGRATIONS: D1Migration[];
    }
  }
}

export {};
