import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { formatDate } from "../src/lib/format-date.mjs";

test("dates use explicit English and UTC, including offset and day rollover", () => {
  assert.equal(formatDate("2026-09-11T19:53:00Z"), "Sep 11, 2026, 7:53 PM UTC");
  assert.equal(formatDate("2026-09-11T13:53:00-06:00"), "Sep 11, 2026, 7:53 PM UTC");
  assert.equal(formatDate("2026-01-01T00:30:00+09:00"), "Dec 31, 2025, 3:30 PM UTC");
});

test("missing dates remain Unknown and invalid dates still fail", () => {
  for (const value of [undefined, null, ""]) assert.equal(formatDate(value), "Unknown");
  assert.throws(() => formatDate("not-a-date"), RangeError);
});

test("environment defaults cannot change date text", () => {
  const moduleUrl = new URL("../src/lib/format-date.mjs", import.meta.url).href;
  for (const [TZ, LANG] of [["UTC", "en_US.UTF-8"], ["America/Denver", "de_DE.UTF-8"], ["Asia/Tokyo", "ja_JP.UTF-8"]]) {
    const result = spawnSync(process.execPath, ["--input-type=module", "-e",
      `import { formatDate } from ${JSON.stringify(moduleUrl)}; process.stdout.write(formatDate("2026-09-11T19:53:00Z"));`,
    ], { env: { ...process.env, TZ, LANG, LC_ALL: LANG }, encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, "Sep 11, 2026, 7:53 PM UTC", `${TZ}, ${LANG}`);
  }
});
