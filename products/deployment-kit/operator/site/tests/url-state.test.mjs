import assert from "node:assert/strict";
import test from "node:test";

import { readQueryValue, replaceQueryState, subscribeQueryState, updateQueryString } from "../src/lib/url-state.mjs";

test("search query state reads a query and handles empty or absent values", () => {
  const search = "?q=review";

  assert.equal(readQueryValue(search, "q", ""), "review");
  assert.equal(readQueryValue("?q=", "q", ""), "");
  assert.equal(readQueryValue("", "q", ""), "");
});

test("URL subscribers follow filter changes and browser navigation until unsubscribed", () => {
  const win = new EventTarget();
  win.location = new URL("https://example.test/catalog?utm=keep#skills");
  win.history = {
    state: null,
    replaceState(_state, _title, url) { win.location = new URL(url, win.location); },
  };
  const searches = [];
  const unsubscribe = subscribeQueryState(() => searches.push(win.location.search), win);

  replaceQueryState({ q: "review" }, { q: "" }, win);
  assert.equal(win.location.href, "https://example.test/catalog?utm=keep&q=review#skills");
  win.location = new URL("https://example.test/catalog?q=python");
  win.dispatchEvent(new Event("popstate"));
  assert.deepEqual(searches, ["?utm=keep&q=review", "?q=python"]);

  unsubscribe();
  replaceQueryState({ q: "" }, { q: "" }, win);
  win.dispatchEvent(new Event("popstate"));
  assert.equal(win.location.search, "");
  assert.equal(searches.length, 2);
});

test("query state updates remove defaults and preserve unrelated params", () => {
  const next = updateQueryString("?utm=keep&q=old", {
    q: "python security",
  }, {
    q: "",
  });

  assert.equal(next, "?utm=keep&q=python+security");
});
