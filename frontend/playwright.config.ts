import { defineConfig } from "@playwright/test";

// Spins up the real FastAPI + LangGraph backend (fake LLM, deterministic) and Vite.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: { baseURL: "http://localhost:5173", trace: "retain-on-failure" },
  webServer: [
    {
      command: "cd ../backend && LLM_PROVIDER=fake uv run uvicorn travel_agent.server:app --port 8000",
      url: "http://localhost:8000/agent/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --port 5173 --strictPort",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
