import { expect, test } from "@playwright/test";

/* spaday-blueprint authored from Python, on a page it shares with a downstream library that imports
 * Blueprint by its bare specifiers. See spaday_blueprint/tests/integration.py.
 */

const PAGE = "http://127.0.0.1:8018";

test("spaday state wires the generated catalog together", async ({ page }) => {
  await page.goto(PAGE);
  const badge = page.locator("#badge");
  await expect(badge).toHaveText("pending");
  await page.locator("#approve").click();
  await expect(badge).toHaveText("approved");
  await page.locator("#reject").click();
  await expect(badge).toHaveText("rejected");
});

test("a library importing Blueprint by name gets the page's copy", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(PAGE);
  await expect(page.locator("#downstream bp-button")).toBeAttached();
  const r = await page.evaluate(() => {
    const downstream = document.querySelector("#downstream bp-button");
    return {
      registered: downstream.constructor === customElements.get("bp-button"),
      upgraded: !!downstream.shadowRoot,
    };
  });
  expect(r).toEqual({ registered: true, upgraded: true });
  // a second copy registering the same tags would have thrown from customElements.define
  expect(errors).toEqual([]);
});

// Blueprint 2.20's number stepper sets its `step` attribute from its constructor, which
// document.createElement rejects, so the check can only see the HTMLUnknownElement it falls back to.
// The test below pins that; drop this exception when it starts failing.
const UPSTREAM_DEFECTS = ["<bp-number-stepper>"];

test("the package's own bundle satisfies its generated catalog", async ({
  page,
}) => {
  await page.goto(PAGE);
  const script = await (
    await page.request.get(`${PAGE}/conformance.js`)
  ).text();
  await expect(page.locator("#approve")).toBeAttached();
  const problems = await page.evaluate(script);
  expect(
    problems.filter((p) => !UPSTREAM_DEFECTS.some((tag) => p.startsWith(tag))),
  ).toEqual([]);
});

test("Blueprint's number stepper still cannot be created with createElement", async ({
  page,
}) => {
  await page.goto(PAGE);
  await expect(page.locator("#approve")).toBeAttached();
  const r = await page.evaluate(() => {
    const Stepper = customElements.get("bp-number-stepper");
    return {
      created: document.createElement("bp-number-stepper") instanceof Stepper,
      constructorSets: new Stepper().getAttributeNames(),
    };
  });
  expect(r).toEqual({ created: false, constructorSets: ["step"] });
});
