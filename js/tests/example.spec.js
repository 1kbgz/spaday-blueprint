import { expect, test } from "@playwright/test";

/* The release console in spaday_blueprint/example.py, run as its own server. */

const PAGE = "http://127.0.0.1:8023";

const tab = (page, name) => page.locator("bp-tab", { hasText: name });

test("streams service load from Python into the cards", async ({ page }) => {
  await page.goto(PAGE);
  const cpu = page.locator('.service[data-id="api"] bp-progress-circle');
  await expect(cpu).toBeVisible();
  const before = await cpu.evaluate((el) => el.value);
  await expect
    .poll(() => cpu.evaluate((el) => el.value), { timeout: 6_000 })
    .not.toBe(before);
});

test("restarts a service through Python and says so in a toast", async ({
  page,
}) => {
  await page.goto(PAGE);
  await page
    .locator('.service[data-id="search"] bp-button', { hasText: "Restart" })
    .click();
  await expect(page.locator("#toast")).toHaveText("Restarted Search");
  await expect(page.locator("#toast")).toBeVisible();
});

test("deploys from the form and watches the rollout land", async ({ page }) => {
  await page.goto(PAGE);
  await tab(page, "Deploy").click();
  await expect(tab(page, "Deploy")).toHaveAttribute("selected");
  await page.locator("#deploy-version").evaluate((el) => {
    el.value = "v2.16.0";
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await page.locator("#deploy").click();
  const message = page.locator("#confirm-message");
  await expect(message).toContainText("Public API v2.16.0 on 6 replicas");
  const id = (await message.textContent()).split(":")[0];
  await page.locator("#confirm-close").click();
  await tab(page, "Services").click();
  const rollout = page.locator(`.rollout[data-id="${id}"]`);
  await expect(rollout).toContainText("Rolling out");
  await expect(rollout).toContainText("Live", { timeout: 15_000 });
});

test("acknowledges an incident through Python", async ({ page }) => {
  await page.goto(PAGE);
  await tab(page, "Incidents").click();
  // Blueprint keeps a button's disabled state as a property, not an attribute
  const id = await page
    .locator(".incidents bp-alert")
    .evaluateAll(
      (alerts) =>
        alerts.find((alert) => !alert.querySelector("bp-button").disabled)
          ?.dataset.id,
    );
  const button = page.locator(`.incidents bp-alert[data-id="${id}"] bp-button`);
  await button.click();
  await expect(button).toHaveJSProperty("disabled", true);
});

test("the dark switch moves Blueprint and the spaday shell to the dark theme", async ({
  page,
}) => {
  await page.goto(PAGE);
  const layer = () =>
    page.evaluate(() =>
      getComputedStyle(document.documentElement)
        .getPropertyValue("--bp-layer-background-200")
        .trim(),
    );
  const light = await layer();
  await page.locator("#dark").click();
  await expect(page.locator("html")).toHaveClass(/wa-dark/);
  expect(await layer()).not.toBe(light);
  const nav = await page
    .locator("spa-nav")
    .evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(
    await page.evaluate(() => {
      const probe = document.createElement("div");
      probe.style.color = "var(--bp-layer-background-200)";
      document.body.append(probe);
      return getComputedStyle(probe).color;
    }),
  ).toBe(nav);
});
