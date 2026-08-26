import assert from "node:assert/strict";
import test from "node:test";

import { RECOMMENDATION_VALUES } from "../src/lib/recommendation-options.mjs";
import { readQueryValue, updateQueryString } from "../src/lib/url-state.mjs";

test("query state reads valid values and rejects unsupported options", () => {
  const search = "?q=review&recommendation=SAFE&sort=last_scanned&tab=assessment";

  assert.equal(readQueryValue(search, "q", ""), "review");
  assert.equal(readQueryValue(search, "recommendation", "all", ["all", "SAFE"]), "SAFE");
  assert.equal(readQueryValue(search, "sort", "name", ["name", "last_scanned"]), "last_scanned");
  assert.equal(readQueryValue("?sort=unexpected", "sort", "name", ["name", "last_scanned"]), "name");
  assert.equal(readQueryValue("?tab=unknown", "tab", "files", ["files", "assessment"]), "files");
});

test("recommendation query state rejects the removed review value", () => {
  assert.deepEqual(RECOMMENDATION_VALUES, ["all", "DO_NOT_INSTALL", "CAUTION", "SAFE", "Unknown"]);
  assert.equal(readQueryValue("?recommendation=REVIEW", "recommendation", "all", RECOMMENDATION_VALUES), "all");
});

test("query state updates remove defaults and preserve unrelated params", () => {
  const next = updateQueryString("?utm=keep&q=old&sort=last_updated", {
    q: "python security",
    sort: "name",
    tab: "assessment",
  }, {
    q: "",
    sort: "name",
    tab: "files",
  });

  assert.equal(next, "?utm=keep&q=python+security&tab=assessment");
});
