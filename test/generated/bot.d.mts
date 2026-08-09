// Types for the esbuild bundle that test/globalSetup.ts writes next to this
// file. The bundle is gitignored; this declaration keeps `tsc --noEmit` working
// whether or not it has been built yet.
export { createBot } from '../../worker/bot/index.js';
