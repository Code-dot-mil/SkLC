import assert from "node:assert/strict";
import test from "node:test";

import { readQueryValue, updateQueryString } from "../src/lib/url-state.mjs";

test("search query state reads a query and handles empty or absent values", () => {
  const search = "?q=review";

  assert.equal(readQueryValue(search, "q", ""), "review");
  assert.equal(readQueryValue("?q=", "q", ""), "");
  assert.equal(readQueryValue("", "q", ""), "");
});

test("query state updates remove defaults and preserve unrelated params", () => {
  const next = updateQueryString("?utm=keep&q=old", {
    q: "python security",
  }, {
    q: "",
  });

  assert.equal(next, "?utm=keep&q=python+security");
});
