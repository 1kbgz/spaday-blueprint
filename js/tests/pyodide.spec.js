import fs from "fs";
import { expect, test } from "@playwright/test";

const built = fs.existsSync("dist/lite/index.html");

async function renderedComponentTags(page, prefix, structuralTags = []) {
  return page.locator("body").evaluate(
    (body, { prefix, structuralTags }) => {
      const components = [...body.querySelectorAll("*")].filter((element) =>
        element.localName.startsWith(prefix),
      );
      const tags = [...new Set(components.map((element) => element.localName))];
      const structural = new Set(structuralTags);
      const unrendered = tags.filter(
        (tag) =>
          !structural.has(tag) &&
          !components
            .filter((element) => element.localName === tag)
            .some((element) => {
              const bounds = element.getBoundingClientRect();
              return bounds.width > 0 && bounds.height > 0;
            }),
      );
      return { count: tags.length, unrendered };
    },
    { prefix, structuralTags },
  );
}

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
  await expect(page.locator("bp-page.mini-page")).toBeVisible();
  await expect(page.locator("bp-page.mini-page bp-header")).toBeVisible();
  await expect(page.locator("bp-page.mini-page bp-panel")).toBeVisible();
  const rendered = await renderedComponentTags(page, "bp-", [
    "bp-dialog",
    "bp-drawer",
    "bp-dropdown",
    "bp-menu",
    "bp-menu-item",
    "bp-option",
    "bp-progress-dot",
    "bp-toast",
    "bp-toggletip",
    "bp-tooltip",
  ]);
  expect(rendered.count).toBe(81);
  expect(rendered.unrendered).toEqual([]);
  await page.locator("bp-button", { hasText: "Open dialog" }).click();
  await expect(page.locator("#gallery-dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await page.locator("bp-button", { hasText: "Open drawer" }).click();
  await expect(page.locator("#gallery-drawer")).toBeVisible();
  await page.keyboard.press("Escape");
  await page.locator("bp-button", { hasText: "Show toast" }).click();
  await expect(page.locator("#gallery-toast")).toBeVisible();
  await expect(page.locator(".token-keyword").first()).toHaveText("from");
});
