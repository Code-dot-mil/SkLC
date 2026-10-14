import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { formatDate } from "../src/lib/format-date.mjs";

test("equivalent timestamps display the same instant in the selected timezone", () => {
  for (const timeZone of ["America/Chicago", "Asia/Tokyo"]) {
    const options = { timeZone };
    assert.equal(
      formatDate("2026-09-11T19:53:00Z", options),
      formatDate("2026-09-11T13:53:00-06:00", options),
    );
    assert.equal(
      formatDate("2026-01-01T00:30:00+09:00", options),
      formatDate("2025-12-31T15:30:00Z", options),
    );
  }
});

test("missing dates remain Unknown and invalid dates still fail", () => {
  for (const value of [undefined, null, ""]) assert.equal(formatDate(value), "Unknown");
  assert.throws(() => formatDate("not-a-date"), RangeError);
});

test("default display follows the viewer's timezone and locale", () => {
  const moduleUrl = new URL("../src/lib/format-date.mjs", import.meta.url).href;
  const display = (TZ, LANG) => {
    const result = spawnSync(process.execPath, ["--input-type=module", "-e",
      `import { formatDate } from ${JSON.stringify(moduleUrl)}; process.stdout.write(formatDate("2026-01-01T00:30:00Z"));`,
    ], { env: { ...process.env, TZ, LANG, LC_ALL: LANG }, encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    return result.stdout;
  };
  const chicago = display("America/Chicago", "en_US.UTF-8");
  const tokyo = display("Asia/Tokyo", "en_US.UTF-8");
  assert.notEqual(chicago, tokyo);
  assert.match(chicago, /2025/); // The same instant is still the previous year here.
  assert.match(tokyo, /2026/);
  assert.notEqual(tokyo, display("Asia/Tokyo", "ja_JP.UTF-8"));
});
