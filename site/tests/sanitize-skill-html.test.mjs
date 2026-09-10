import assert from "node:assert/strict";
import test from "node:test";

import { sanitizeSkillHtml } from "../src/lib/sanitize-skill-html.mjs";

test("skill markdown sanitizer removes executable HTML", () => {
  const unsafe = '<h1>Skill</h1><script>alert(1)</script><img src="x" onerror="alert(2)"><p onclick="alert(3)">Use it</p>';
  const safe = sanitizeSkillHtml(unsafe);

  assert.equal(safe.includes("<script"), false);
  assert.equal(safe.includes("onerror"), false);
  assert.equal(safe.includes("onclick"), false);
  assert.equal(safe.includes("<h1>Skill</h1>"), true);
  assert.equal(safe.includes("<p>Use it</p>"), true);
});
