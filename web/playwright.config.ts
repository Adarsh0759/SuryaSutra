import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
  },
  webServer: [
    {
      command:
        'D:/Projects/SuryaSutra/.venv/Scripts/python.exe -m uvicorn suryasutra.api.main:app --port 8000',
      cwd: 'D:/Projects/SuryaSutra',
      url: 'http://127.0.0.1:8000/health',
      timeout: 120_000,
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1',
      url: 'http://127.0.0.1:5173',
      timeout: 60_000,
      reuseExistingServer: true,
    },
  ],
})
