import assert from "node:assert/strict";
import test from "node:test";

import { relativeSiteRoot } from "../src/lib/portable-paths.mjs";

test("pages use a relative base that returns to the packaged site root", () => {
  assert.equal(relativeSiteRoot("/"), "./");
  assert.equal(relativeSiteRoot("/skills/example/"), "../../");
  assert.equal(relativeSiteRoot("/skills/example/?tab=assessment#summary"), "../../");
});

test("site links resolve beneath root and project-path deployments", () => {
  for (const deploymentRoot of [
    "https://pages.example/",
    "https://pages.example/group/project/",
  ]) {
    for (const documentName of ["", "index.html"]) {
      const catalogDocument = new URL(documentName, deploymentRoot);
      const catalogBase = new URL(relativeSiteRoot("/"), catalogDocument);
      assert.equal(new URL("assets/site.css", catalogBase).href, `${deploymentRoot}assets/site.css`);
      assert.equal(new URL("skills/example/", catalogBase).href, `${deploymentRoot}skills/example/`);

      const detailDocument = new URL(`skills/example/${documentName}`, deploymentRoot);
      const detailBase = new URL(relativeSiteRoot("/skills/example/"), detailDocument);
      assert.equal(detailBase.href, deploymentRoot);
      assert.equal(new URL("./", detailBase).href, deploymentRoot);
      assert.equal(new URL("downloads/example.zip", detailBase).href, `${deploymentRoot}downloads/example.zip`);
      assert.equal(new URL("./assets/client.js", detailBase).href, `${deploymentRoot}assets/client.js`);
    }
  }
});
