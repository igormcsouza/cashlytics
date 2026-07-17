import { defineConfig, devices } from "@playwright/test";

// End-to-end tests run against a locally running stack:
//   - backend API on http://localhost:5000 (via the API gateway proxy)
//   - cognito-local on http://localhost:9229 (auth_bootstrap.py's dev admin)
//   - Next.js frontend on http://localhost:3000 (NEXT_PUBLIC_API_BASE_URL -> :5000)
// `make up && make ui` starts all three (see README / e2e launcher).
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
