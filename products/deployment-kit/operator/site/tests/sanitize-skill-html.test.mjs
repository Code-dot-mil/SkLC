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

test("skill markdown sanitizer strips dangerous attributes separated by mixed whitespace", () => {
  const safe = sanitizeSkillHtml(
    '<a \t\nhref = " javascript:alert(1)" \tONCLICK = alert(2)>Read</a>' +
    '<img\nsrc="data:text/html,unsafe"\tonerror=alert(3) alt="Skill">' +
    '<a href="https://example.com/skill">Safe link</a>'
  );

  assert.doesNotMatch(safe, /javascript:|data:text\/html|onclick|onerror/i);
  assert.match(safe, />Read<\/a>/);
  assert.match(safe, /alt="Skill"/);
  assert.match(safe, /href="https:\/\/example.com\/skill"/);
});
