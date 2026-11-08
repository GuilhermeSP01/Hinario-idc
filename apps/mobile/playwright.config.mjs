import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.mjs',
  workers: 1,
  reporter: 'line',
  use: {
    baseURL: 'http://127.0.0.1:5180',
    launchOptions: process.env.BROWSER_PATH ? { executablePath: process.env.BROWSER_PATH } : {},
  },
  webServer: {
    command: 'corepack pnpm --filter @hinario/mobile dev --host 127.0.0.1 --port 5180 --strictPort --mode test',
    cwd: fileURLToPath(new URL('../..', import.meta.url)),
    url: 'http://127.0.0.1:5180',
    reuseExistingServer: false,
    env: { VITE_FIREBASE_API_KEY: '', VITE_FIREBASE_PROJECT_ID: '', VITE_FIREBASE_APP_ID: '', VITE_LOG_LEVEL: 'error' },
  },
});
