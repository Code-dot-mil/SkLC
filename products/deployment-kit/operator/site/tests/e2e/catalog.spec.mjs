import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

async function followDownload(page, link, filename) {
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  expect(download.suggestedFilename()).toBe(filename);
  expect(await download.failure()).toBeNull();
  return download.path();
}

test("find a skill, read its evidence and download its package", async ({ page, baseURL }) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("response", response => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("./");
  await expect(page.getByRole("contentinfo")).toContainText(process.env.SKLC_SITE_REVISION.slice(0, 8));
  const skills = page.getByRole("article");
  const firstSkill = skills.first().getByRole("heading").getByRole("link");
  await expect(firstSkill).toBeVisible();
  const skillId = await firstSkill.innerText();
  const initialCount = await skills.count();
  const search = page.getByRole("textbox", { name: "Search" });
  await search.fill("sklc-e2e-no-such-skill-73c92e1a");
  await expect(skills).toHaveCount(0);
  await search.fill("");
  await expect(skills).toHaveCount(initialCount);
  await search.fill(skillId);
  await page.getByRole("link", { name: skillId, exact: true }).click();
  await expect(page.locator("header").getByRole("heading", { level: 1, name: skillId, exact: true })).toBeVisible();
  const instructions = page.getByRole("tabpanel", { name: "Instructions", exact: true }).locator(".markdown-body");
  await expect(instructions).toBeVisible();
  await expect(instructions).toHaveText(/\S/, { useInnerText: true });

  const files = join(process.env.SKLC_SITE_DIR, "downloads");
  const filename = `${skillId}.zip`;
  const archive = await followDownload(page, page.getByRole("link", { name: "Download skill package" }), filename);
  expect(await readFile(archive)).toEqual(await readFile(join(files, filename)));
  // Reading the ZIP entry checks its CRC and UTF-8 text.
  const instructionLength = execFileSync("python", [
    "-c", `import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as package:
    print(len(package.read(sys.argv[2]).decode("utf-8").strip()))`,
    archive, `${skillId}/SKILL.md`,
  ], { encoding: "utf8" });
  expect(Number(instructionLength)).toBeGreaterThan(0);

  await page.getByRole("tab", { name: "Assessment Evidence" }).click();
  const reports = join(files, "assessments", skillId);
  const adjudication = await followDownload(page, page.getByRole("link", { name: "Download adjudication.json" }), "adjudication.json");
  const decision = await readFile(adjudication);
  expect(JSON.parse(decision).findings).toEqual(expect.any(Array));
  expect(decision).toEqual(await readFile(join(reports, "adjudication.json")));

  // The scanner link opens its native JSON report in the browser.
  const [scannerResponse] = await Promise.all([
    page.waitForResponse(response => response.request().isNavigationRequest()),
    page.getByRole("link", { name: /download .*scanner output/i }).click(),
  ]);
  expect(scannerResponse.ok()).toBe(true);
  const scan = await scannerResponse.body();
  expect(JSON.parse(scan).issues).toEqual(expect.any(Array));
  expect(scan).toEqual(await readFile(join(reports, "skillspector.json")));
  await page.goBack();
  await page.getByRole("link", { name: "Back to catalog" }).click();
  await expect(page).toHaveURL(baseURL);
  await expect(skills).toHaveCount(initialCount);
  expect(errors).toEqual([]);
});
