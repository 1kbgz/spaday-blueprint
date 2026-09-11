import { defineConfig, devices } from "@playwright/test";

const pyodideOnly = process.env.SPADAY_BLUEPRINT_PYODIDE_ONLY === "1";

export default defineConfig({
  testDir: "tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["line"],
    ["html", { outputFile: "playwright-report/index.html", open: "never" }],
    ["junit", { outputFile: "junit.xml" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "pnpm run start:tests",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
    ...(pyodideOnly
      ? []
      : [
          {
            command: "python -m spaday_blueprint.example",
            url: "http://127.0.0.1:8023",
            reuseExistingServer: !process.env.CI,
            timeout: 120 * 1000,
          },
          {
            // by path, not `-m`: the tests directory is not an importable package
            command: "python ../spaday_blueprint/tests/integration.py",
            url: "http://127.0.0.1:8018",
            reuseExistingServer: !process.env.CI,
            timeout: 120 * 1000,
          },
        ]),
  ],
});
