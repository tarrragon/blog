import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for blog regression tests.
 *
 * Tests assume `make site` has been run — they hit the static `public/` build
 * via a local file server. This avoids needing Hugo dev server (faster + more
 * deterministic — search index is the production index, not dev mode).
 *
 * To run: npm test
 * To run interactively: npm run test:ui
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',

  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /**
   * Serve `public/` over a static server during tests.
   * Hugo's baseURL is `https://tarrragon.github.io/blog/` so production HTML
   * uses `/blog/...` paths. To match this locally we mount `public/` at
   * `/blog/` via a symlink in `.test-www/` (gitignored).
   *
   * Pre-requisite: run `make site` before running tests.
   */
  webServer: {
    command:
      'mkdir -p .test-www && ln -sfn ../public .test-www/blog && ' +
      'npx http-server .test-www -p 4173 -s --cors',
    url: 'http://localhost:4173/blog/search/',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
