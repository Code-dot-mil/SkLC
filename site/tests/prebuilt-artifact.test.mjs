import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { once } from "node:events";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, symlinkSync, unlinkSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

test("built site links and assets work unchanged at root and nested hosting paths", async (t) => {
  const root = mkdtempSync(resolve(tmpdir(), "sklc-prebuilt-site-"));
  const fixtureSite = resolve(root, "site");
  const dependencies = resolve(fixtureSite, "node_modules");
  t.after(() => {
    // Remove only the dependency link before deleting this test's own files.
    if (existsSync(dependencies)) unlinkSync(dependencies);
    rmSync(root, { recursive: true, force: true });
  });
  mkdirSync(fixtureSite);
  for (const name of ["src", "scripts", "astro.config.mjs", "package.json", "tsconfig.json"]) {
    cpSync(resolve(siteRoot, name), resolve(fixtureSite, name), { recursive: true });
  }
  symlinkSync(resolve(siteRoot, "node_modules"), dependencies, process.platform === "win32" ? "junction" : "dir");
  writeFixture(root);
  const env = {
    ...process.env,
    ASTRO_TELEMETRY_DISABLED: "1",
    SKILL_EXCHANGE_REPOSITORY_ROOT: root,
    SKILL_EXCHANGE_GENERATED_ROOT: resolve(root, ".exchange/generated"),
  };
  const astroPackage = JSON.parse(readFileSync(resolve(dependencies, "astro/package.json"), "utf-8"));
  for (const args of [
    [resolve(fixtureSite, "scripts/copy-downloads.mjs")],
    [resolve(dependencies, "astro", astroPackage.bin.astro), "build"],
  ]) {
    const result = spawnSync(process.execPath, args, { cwd: fixtureSite, env, encoding: "utf-8", timeout: 120_000 });
    assert.equal(result.status, 0, `${result.error || ""}\n${result.stdout}\n${result.stderr}`);
  }

  const dist = resolve(fixtureSite, "dist");
  assert.ok(statSync(resolve(dist, "assets")).isDirectory());
  assert.ok(!existsSync(resolve(dist, "_astro")));
  for (const mount of ["/", "/group/project/"]) {
    await t.test(`serve the same build at ${mount}`, async () => {
      const server = createServer((request, response) => {
        const pathname = new URL(request.url, "http://localhost").pathname;
        const relative = decodeURIComponent(pathname.slice(mount.length));
        let file = resolve(dist, relative || "index.html");
        if (pathname.endsWith("/") && relative) file = resolve(file, "index.html");
        if (!pathname.startsWith(mount) || !file.startsWith(dist + sep) || !existsSync(file) || !statSync(file).isFile()) {
          response.writeHead(404).end();
          return;
        }
        response.end(readFileSync(file));
      });
      server.listen(0, "127.0.0.1");
      await once(server, "listening");
      try {
        const deployment = `http://127.0.0.1:${server.address().port}${mount}`;
        const targets = new Set();
        for (const page of ["", "index.html", "skills/ai4sdlc/example/", "skills/ai4sdlc/example/index.html"]) {
          const document = new URL(page, deployment);
          const response = await fetch(document);
          assert.equal(response.status, 200, document.href);
          const html = await response.text();
          const baseTag = html.match(/<base\s+href="([^"]+)"/);
          assert.ok(baseTag, `missing relative base in ${page}`);
          assert.ok(!baseTag[1].startsWith("/"));
          const base = new URL(baseTag[1], document);
          assert.equal(base.href, deployment);
          for (const [, attribute, value] of html.matchAll(/\b(href|src|component-url|renderer-url)="([^"]+)"/g)) {
            if (value === baseTag[1] && attribute === "href") continue;
            const target = new URL(value.replaceAll("&amp;", "&"), base);
            if (target.origin !== document.origin) continue;
            assert.ok(!value.startsWith("/"), `root-absolute ${attribute}: ${value}`);
            assert.ok(target.href.startsWith(deployment), `link escapes deployment: ${target.href}`);
            assert.equal((await fetch(target)).status, 200, target.href);
            targets.add(target.pathname.slice(mount.length));
          }
        }
        assert.ok(targets.has("skills/ai4sdlc/example/"), "catalog detail link was not checked");
        assert.ok(targets.has(""), "back-to-catalog link was not checked");
        assert.ok(targets.has("downloads/example.zip"), "skill download was not checked");
        assert.ok(targets.has("downloads/scanner-runs/run-1/skillspector.json"), "scanner download was not checked");
        assert.ok([...targets].some((path) => path.startsWith("assets/") && path.endsWith(".css")));
        assert.ok([...targets].some((path) => path.startsWith("assets/") && path.endsWith(".js")));
      } finally {
        server.closeAllConnections();
        await new Promise((done, reject) => server.close((error) => error ? reject(error) : done()));
      }
    });
  }
});

function writeFixture(root) {
  const generated = resolve(root, ".exchange/generated");
  const write = (path, value) => {
    const destination = resolve(generated, path);
    mkdirSync(dirname(destination), { recursive: true });
    writeFileSync(destination, value);
  };
  const timestamp = "2026-01-01T00:00:00Z";
  write("index.json", JSON.stringify({ skills: [{
    namespace: "ai4sdlc", skill_id: "example", display_id: "ai4sdlc/example", name: "example",
    description: "Portable site test skill", tags: [], recommendation: "SAFE", confidence_flags: [],
    last_updated: timestamp, first_observed: timestamp, last_scanned: timestamp,
    scan_mode: "static-only", content_hash: "abc123", skill_files: [],
    skill_md_content: "---\nname: example\ndescription: Portable site test skill\n---\n# Example\n",
    download_path: "downloads/example.zip",
  }] }));
  write("tables/scanner_runs.json", JSON.stringify({ rows: [{
    id: "run-1", namespace: "ai4sdlc", skill_id: "example", last_scanned: timestamp,
    scanner_name: "skillspector", scan_mode: "static-only", content_hash: "abc123",
    display_risk: "Low", confidence_flags: [], native_severity: "LOW", native_score: 0,
  }] }));
  write("tables/scanner_findings.json", JSON.stringify({ rows: [] }));
  write("tables/scanner_artifacts.json", JSON.stringify({ rows: [{
    id: "run-1:native_report", scanner_run_id: "run-1", artifact_kind: "native_report",
    path: ".exchange/generated/scanner-runs/run-1/skillspector.json",
    download_path: "downloads/scanner-runs/run-1/skillspector.json",
  }] }));
  write("scanner-runs/run-1/skillspector.json", "{}\n");
  // An empty, valid ZIP: this test checks serving, not skill-package contents.
  write("zips/example.zip", Buffer.from("504b0506000000000000000000000000000000000000", "hex"));
}
