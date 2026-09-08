import assert from "node:assert/strict";
import test from "node:test";

import { relativeSiteRoot } from "../src/lib/portable-paths.mjs";

test("pages use a relative base that returns to the packaged site root", () => {
  assert.equal(relativeSiteRoot("/"), "./");
  assert.equal(relativeSiteRoot("/skills/ai4sdlc/example/"), "../../../");
});

test("site links resolve beneath root and project-path deployments", () => {
  for (const deploymentRoot of [
    "https://pages.example/",
    "https://pages.example/group/project/",
  ]) {
    const catalogDocument = new URL("index.html", deploymentRoot);
    const catalogBase = new URL(relativeSiteRoot("/"), catalogDocument);
    assert.equal(new URL("assets/site.css", catalogBase).href, `${deploymentRoot}assets/site.css`);
    assert.equal(
      new URL("skills/ai4sdlc/example/", catalogBase).href,
      `${deploymentRoot}skills/ai4sdlc/example/`,
    );

    const detailDocument = new URL("skills/ai4sdlc/example/index.html", deploymentRoot);
    const detailBase = new URL(relativeSiteRoot("/skills/ai4sdlc/example/"), detailDocument);
    assert.equal(detailBase.href, deploymentRoot);
    assert.equal(new URL("downloads/example.zip", detailBase).href, `${deploymentRoot}downloads/example.zip`);
  }
});
