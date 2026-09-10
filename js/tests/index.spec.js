import { expect, test } from "@playwright/test";

test("registers and renders the Blueprint catalog", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/dist/index.html");
  await page.evaluate(() => {
    const button = document.createElement("bp-button");
    button.textContent = "Run";
    document.body.appendChild(button);
  });
  await expect
    .poll(() =>
      page.locator("bp-button").evaluate((button) => !!button.shadowRoot),
    )
    .toBe(true);
  expect(
    await page.evaluate(() => ({
      icon: !!customElements.get("bp-icon"), // registered by the icons package
      tooltip: !!customElements.get("bp-tooltip"),
    })),
  ).toEqual({ icon: true, tooltip: true });
  expect(errors).toEqual([]);
});

test("survives an application that already registered a Blueprint element", async ({
  page,
}) => {
  // an app shipping its own copy of Blueprint registers `bp-button` first; without the define-guard
  // this bundle throws from `customElements.define` and the page renders no Blueprint at all
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.addInitScript(() => {
    customElements.define("bp-button", class extends HTMLElement {});
  });
  await page.goto("/dist/index.html");
  await page.waitForFunction(() => !!customElements.get("bp-card"));
  expect(errors).toEqual([]);
  expect(
    await page.evaluate(() => ({
      theirs: !document.createElement("bp-button").shadowRoot,
      restored: String(customElements.define).includes("native code"),
    })),
  ).toEqual({ theirs: true, restored: true });
});

test("publishes the Blueprint version it serves", async ({ page }) => {
  await page.goto("/dist/index.html");
  await page.waitForFunction(() => !!globalThis.__spadayBlueprint);
  expect(
    await page.evaluate(() => globalThis.__spadayBlueprint.version),
  ).toMatch(/^\d+\.\d+\.\d+/);
});

test("a Blueprint token set on the app drives the shell palette inside it", async ({
  page,
}) => {
  // what `App().css(bp_status_accent_background_200=...)` renders
  await page.goto("/dist/index.html");
  expect(
    await page.evaluate(() => {
      const app = document.createElement("spa-app");
      app.style.setProperty(
        "--bp-status-accent-background-200",
        "rgb(255, 0, 0)",
      );
      const probe = document.createElement("div");
      probe.style.color = "var(--spa-accent)";
      app.append(probe);
      document.body.append(app);
      return getComputedStyle(probe).color;
    }),
  ).toBe("rgb(255, 0, 0)");
});

test("follows spaday's page mode, islands included", async ({ page }) => {
  await page.goto("/dist/index.html");
  const r = await page.evaluate(() => {
    const token = (el, name) => getComputedStyle(el).getPropertyValue(name);
    const root = document.documentElement;
    const light = {
      bp: token(root, "--bp-layer-background-200"),
      spa: token(root, "--spa-surface"),
    };
    root.classList.add("wa-dark");
    const dark = {
      bp: token(root, "--bp-layer-background-200"),
      spa: token(root, "--spa-surface"),
    };
    // a light island inside the dark page flips back
    const island = document.createElement("div");
    island.className = "wa-light";
    document.body.appendChild(island);
    return { light, dark, island: token(island, "--spa-surface") };
  });
  expect(r.dark.bp).not.toBe(r.light.bp);
  expect(r.dark.spa).not.toBe(r.light.spa); // the shell palette follows Blueprint's theme
  expect(r.island).toBe(r.light.spa);
});
