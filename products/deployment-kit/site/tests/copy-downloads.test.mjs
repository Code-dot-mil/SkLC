import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const testDir = dirname(fileURLToPath(import.meta.url));
const script = resolve(testDir, "../scripts/copy-downloads.mjs");

test("copy-downloads rejects artifact sources outside the generated scanner tree", () => {
  const root = mkdtempSync(resolve(tmpdir(), "skill-exchange-copy-downloads-"));
  const siteDir = resolve(root, "products", "deployment-kit", "site");
  const generatedTables = resolve(root, "maintainer", "exchange", "generated", "tables");
  mkdirSync(siteDir, { recursive: true });
  mkdirSync(generatedTables, { recursive: true });
  writeFileSync(resolve(root, "secret.txt"), "secret\n");
  writeFileSync(
    resolve(generatedTables, "scanner_artifacts.json"),
    JSON.stringify({
      rows: [
        {
          path: "secret.txt",
          download_path: "downloads/scanner-runs/run-1/secret.txt",
        },
      ],
    }),
  );

  const completed = runCopyDownloads(siteDir);

  assert.notEqual(completed.status, 0);
  assert.match(completed.stderr, /outside maintainer\/exchange\/generated\/scanner-runs/);
});

test("copy-downloads rejects destinations outside public downloads", () => {
  const root = mkdtempSync(resolve(tmpdir(), "skill-exchange-copy-downloads-"));
  const siteDir = resolve(root, "products", "deployment-kit", "site");
  const scannerRun = resolve(root, "maintainer", "exchange", "generated", "scanner-runs", "run-1");
  const generatedTables = resolve(root, "maintainer", "exchange", "generated", "tables");
  mkdirSync(siteDir, { recursive: true });
  mkdirSync(scannerRun, { recursive: true });
  mkdirSync(generatedTables, { recursive: true });
  writeFileSync(resolve(scannerRun, "skillspector.json"), "{}\n");
  writeFileSync(
    resolve(generatedTables, "scanner_artifacts.json"),
    JSON.stringify({
      rows: [
        {
          path: "maintainer/exchange/generated/scanner-runs/run-1/skillspector.json",
          download_path: "/../src/pages/overwrite.astro",
        },
      ],
    }),
  );

  const completed = runCopyDownloads(siteDir);

  assert.notEqual(completed.status, 0);
  assert.match(completed.stderr, /outside public\/downloads/);
});

test("copy-downloads rebases generated artifact paths from another checkout", () => {
  const root = mkdtempSync(resolve(tmpdir(), "skill-exchange-copy-downloads-"));
  const siteDir = resolve(root, "products", "deployment-kit", "site");
  const scannerRun = resolve(root, "maintainer", "exchange", "generated", "scanner-runs", "run-1");
  const generatedTables = resolve(root, "maintainer", "exchange", "generated", "tables");
  mkdirSync(siteDir, { recursive: true });
  mkdirSync(scannerRun, { recursive: true });
  mkdirSync(generatedTables, { recursive: true });
  writeFileSync(resolve(scannerRun, "skillspector.json"), "{\"risk\":\"low\"}\n");
  writeFileSync(
    resolve(generatedTables, "scanner_artifacts.json"),
    JSON.stringify({
      rows: [
        {
          path: "/previous/checkout/maintainer/exchange/generated/scanner-runs/run-1/skillspector.json",
          download_path: "downloads/scanner-runs/run-1/skillspector.json",
        },
      ],
    }),
  );

  const completed = runCopyDownloads(siteDir);

  assert.equal(completed.status, 0, completed.stderr);
  assert.equal(
    readFileSync(resolve(siteDir, "public", "downloads", "scanner-runs", "run-1", "skillspector.json"), "utf-8"),
    "{\"risk\":\"low\"}\n",
  );
});

test("copy-downloads uses the configured generated root", () => {
  const root = mkdtempSync(resolve(tmpdir(), "skill-exchange-copy-downloads-"));
  const siteDir = resolve(root, "products", "deployment-kit", "site");
  const generatedRoot = resolve(root, "maintainer", "exchange", "local-generated");
  const zipDir = resolve(generatedRoot, "zips");
  mkdirSync(siteDir, { recursive: true });
  mkdirSync(zipDir, { recursive: true });
  writeFileSync(resolve(zipDir, "example.zip"), "zip bytes\n");

  const completed = runCopyDownloads(siteDir, {
    SKILL_EXCHANGE_GENERATED_ROOT: generatedRoot,
  });

  assert.equal(completed.status, 0, completed.stderr);
  assert.equal(readFileSync(resolve(siteDir, "public", "downloads", "example.zip"), "utf-8"), "zip bytes\n");
});

function runCopyDownloads(siteDir, environment = {}) {
  return spawnSync("node", [script], {
    cwd: siteDir,
    encoding: "utf-8",
    env: { ...process.env, ...environment },
  });
}
