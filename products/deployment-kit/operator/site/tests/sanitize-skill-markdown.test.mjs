import assert from "node:assert/strict";
import test from "node:test";

import { createMarkdownProcessor } from "@astrojs/markdown-remark";

import { sanitizeSkillMarkdown } from "../src/lib/sanitize-skill-markdown.mjs";

test("renders contributor raw HTML as inert text", async () => {
  const processor = await createMarkdownProcessor({
    rehypePlugins: [sanitizeSkillMarkdown],
  });
  const unsafe = '<form action="javascript:alert(1)"><button>Download</button></form>';

  const rendered = await processor.render(unsafe);

  assert.doesNotMatch(rendered.code, /<form\b/i);
  assert.doesNotMatch(rendered.code, /<button\b/i);
  assert.match(rendered.code, /(?:&lt;|&#x3c;)form\b/i);
});
