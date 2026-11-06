import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const script = resolve(dirname(fileURLToPath(import.meta.url)), "../scripts/copy-downloads.mjs");

function fixture(t) {
  const root = mkdtempSync(resolve(tmpdir(), "skill-exchange-downloads-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const site = resolve(root, "site");
  const generated = resolve(root, ".exchange/generated");
  mkdirSync(resolve(site, "scripts"), { recursive: true });
  cpSync(script, resolve(site, "scripts/copy-downloads.mjs"));
  mkdirSync(resolve(generated, "zips"), { recursive: true });
  mkdirSync(resolve(generated, "assessments/example"), { recursive: true });
  const skill = {
    download_path: "downloads/example.zip",
    assessment_downloads: {
      skillspector: "downloads/assessments/example/skillspector.json",
      adjudication: "downloads/assessments/example/adjudication.json",
    },
  };
  writeFileSync(resolve(generated, "zips/example.zip"), "package");
  for (const filename of ["skillspector.json", "adjudication.json"]) {
    writeFileSync(resolve(generated, "assessments/example", filename), JSON.stringify({ report: filename }));
  }
  return { root, site, generated, skill };
}

function run({ site, generated, skill }) {
  writeFileSync(resolve(generated, "index.json"), JSON.stringify({ skills: [skill] }));
  return spawnSync(process.execPath, [resolve(site, "scripts/copy-downloads.mjs")], {
    cwd: dirname(site), encoding: "utf-8",
  });
}

test("copies the skill package and exact report pair from the standard generated directory regardless of working directory", (t) => {
  const data = fixture(t);
  const result = run(data);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(readFileSync(resolve(data.site, "public/downloads/example.zip"), "utf-8"), "package");
  for (const filename of ["skillspector.json", "adjudication.json"]) {
    assert.deepEqual(JSON.parse(readFileSync(resolve(data.site, "public/downloads/assessments/example", filename))), { report: filename });
  }
});

for (const escape of ["../secret.zip", "../assessments/example/skillspector.json"]) {
  test(`rejects a download escaping its generated source: ${escape}`, (t) => {
    const data = fixture(t);
    data.skill.download_path = `downloads/${escape}`;
    const result = run(data);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /outside generated product data/);
  });
}

test("rejects report symlinks outside generated assessments", (t) => {
  const data = fixture(t);
  const report = resolve(data.generated, "assessments/example/skillspector.json");
  rmSync(report);
  writeFileSync(resolve(data.root, "secret.json"), "secret");
  symlinkSync(resolve(data.root, "secret.json"), report);
  const result = run(data);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /outside generated product data/);
});

test("fails when an indexed assessment report is missing", (t) => {
  const data = fixture(t);
  rmSync(resolve(data.generated, "assessments/example/adjudication.json"));
  assert.notEqual(run(data).status, 0);
});

test("fails when the generated catalog index is missing", (t) => {
  const { root, site } = fixture(t);
  const result = spawnSync(process.execPath, [resolve(site, "scripts/copy-downloads.mjs")], {
    cwd: root, encoding: "utf-8",
  });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ENOENT/);
});
