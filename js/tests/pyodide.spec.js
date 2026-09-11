import fs from "fs";
import { expect, test } from "@playwright/test";

const built = fs.existsSync("dist/lite/index.html");

async function waitForPython(page) {
  await page.waitForFunction(
    () =>
      document.documentElement.dataset.ready === "true" ||
      document.querySelector("#pyodide-status")?.textContent ===
        "Unable to start",
    undefined,
    { timeout: 150_000 },
  );
  await expect(page.locator("html")).toHaveAttribute("data-ready", "true");
}

test("runs the complete example in Pyodide", async ({ page }) => {
  test.skip(!built, "run `make pyodide-example` first");
  test.setTimeout(180_000);

  await page.goto("/dist/lite/index.html");
  await waitForPython(page);
  await expect(page.locator("h1")).toHaveText("Release control");
  const cpu = page.locator('.service[data-id="api"] bp-progress-circle');
  await expect(cpu).toBeVisible();
  const initial = await cpu.evaluate((element) => element.value);
  await expect
    .poll(() => cpu.evaluate((element) => element.value), { timeout: 5_000 })
    .not.toBe(initial);

  await page
    .locator('.service[data-id="search"] bp-button', { hasText: "Restart" })
    .click();
  await expect(page.locator("#toast")).toHaveText("Restarted Search");
});

test("runs the component gallery in Pyodide", async ({ page }) => {
  test.skip(!built, "run `make pyodide-example` first");
  test.setTimeout(180_000);

  await page.goto("/dist/lite/?example=gallery");
  await waitForPython(page);
  await expect(page.locator("h1")).toHaveText("Component gallery");
  expect(await page.locator("bp-card.gallery-card").count()).toBeGreaterThan(
    20,
  );
  await expect(page.locator("bp-tree-item").first()).toBeVisible();
  await expect(page.locator(".token-keyword").first()).toHaveText("from");
});
