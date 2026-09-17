import { expect, test } from "@playwright/test";

const PAGE = "http://127.0.0.1:8030";
const input = (page, id) => page.locator(`#${id} input`).last();
const textarea = (page, id) => page.locator(`#${id} textarea`).last();

test("renders Blueprint controls and the explicit radio fallback", async ({
  page,
}) => {
  await page.goto(PAGE);
  await page.locator("#dialog").waitFor({ state: "attached" });
  expect(
    await page.evaluate(() =>
      [
        "save",
        "name",
        "notes",
        "count",
        "date",
        "agree",
        "dark",
        "plan",
        "priority",
        "volume",
        "alert",
        "progress",
        "dialog",
      ].map((id) => document.getElementById(id).localName),
    ),
  ).toEqual([
    "bp-button",
    "bp-input",
    "bp-textarea",
    "bp-number",
    "bp-date",
    "bp-checkbox",
    "bp-switch",
    "bp-select",
    "spa-radio-group",
    "bp-range",
    "bp-alert",
    "bp-progress-bar",
    "bp-dialog",
  ]);
  await expect(page.locator("[data-ui-fallback]")).toHaveCount(1);
});

test("values round-trip through Blueprint controls", async ({ page }) => {
  await page.goto(PAGE);
  const state = page.locator("#state");
  await expect(state).toHaveText(
    "||2|2026-09-14|false|false|basic|1|5|25|false|false",
  );
  await input(page, "name").fill("Ada");
  await textarea(page, "notes").fill("Ready");
  await input(page, "count").fill("4");
  await input(page, "date").fill("2026-10-01");
  await page.locator("#agree").click();
  await page.locator("#dark").click();
  await page.getByRole("radio", { name: "High" }).click();
  await page.locator("#volume").evaluate((element) => {
    element.value = 8;
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await expect(state).toHaveText(
    "Ada|Ready|4|2026-10-01|true|true|basic|2|8|25|false|false",
  );
});

test("select, actions, and dialog stay bound", async ({ page }) => {
  await page.goto(PAGE);
  await page.locator("#plan").click();
  await page.getByRole("option", { name: "Plus" }).click();
  await expect(page.locator("#state")).toContainText("|plus|");
  await page.locator("#save").click();
  await expect(page.locator("#state")).toContainText("|true|false");

  const dialog = page.locator("#dialog");
  await expect(dialog).toHaveJSProperty("open", false);
  await page.locator("#open").click();
  await expect(dialog).toHaveJSProperty("open", true);
  await page.locator("#close").click();
  await expect(dialog).toHaveJSProperty("open", false);
});

test("labels, help, errors, feedback, and disabled state render", async ({
  page,
}) => {
  await page.goto(PAGE);
  await expect(page.getByText("Your name")).toBeVisible();
  await expect(page.getByText("Required")).toBeVisible();
  await expect(page.locator("#never")).toHaveJSProperty("disabled", true);
  await expect(page.locator("#save")).toHaveText("Save");
  await expect(page.locator("#save")).toHaveAttribute("status", "accent");
  await expect(page.locator("#alert")).toContainText("Portable");
  await expect(page.locator("#progress")).toHaveJSProperty("value", 25);
});
