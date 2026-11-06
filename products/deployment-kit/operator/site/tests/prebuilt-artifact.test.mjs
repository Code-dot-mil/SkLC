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
  for (const name of ["src", "scripts", "public", "astro.config.mjs", "package.json", "tsconfig.json"]) {
    cpSync(resolve(siteRoot, name), resolve(fixtureSite, name), { recursive: true });
  }
  symlinkSync(resolve(siteRoot, "node_modules"), dependencies, process.platform === "win32" ? "junction" : "dir");
  writeFixture(root);
  const env = {
    ...process.env,
    ASTRO_TELEMETRY_DISABLED: "1",
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
  const renderedText = (page) => readFileSync(resolve(dist, page, "index.html"), "utf-8")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/g, "")
    .replace(/<[^>]*>/g, " ");
  const detail = renderedText("skills/example");
  assert.ok(detail.includes("Jun 19, 2020"), "creation estimate must survive the static build");
  assert.ok(detail.includes("Oct 20, 2025"), "last update must remain distinct from scan time");
  for (const expected of ["Fixture adjudication summary", "Adjudication status", "Coverage sufficient", "external references were not assessed", "2026"]) {
    assert.ok(detail.includes(expected), `missing assessment outcome: ${expected}`);
  }
  const html = readFileSync(resolve(dist, "skills/example/index.html"), "utf-8");
  assert.ok(!/<script[^>]*>alert\(1\)/.test(html), "summary HTML must stay inert");
  assert.ok(!html.includes('href="https://untrusted.example/"'), "summary links must stay inert");
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
        for (const page of ["", "index.html", "skills/example/", "skills/example/index.html"]) {
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
        assert.ok(targets.has("skills/example/"), "catalog detail link was not checked");
        assert.ok(targets.has(""), "back-to-catalog link was not checked");
        assert.ok(targets.has("downloads/example.zip"), "skill download was not checked");
        assert.ok(targets.has("downloads/assessments/example/skillspector.json"), "scanner download was not checked");
        assert.ok(targets.has("downloads/assessments/example/adjudication.json"), "adjudication download was not checked");
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
  const example = {
    skill_id: "example", name: "Example skill",
    description: "Portable site test skill", last_updated: "2025-10-20T12:00:00Z",
    first_observed: "2020-06-19T12:00:00Z", last_scanned: timestamp,
    skill_files: [{ path: "SKILL.md", size_bytes: 100 }],
    skill_md_content: "---\nname: example\ndescription: Portable site test skill\n---\n# Example instructions\nRead the complete instructions before use.\n",
    download_path: "downloads/example.zip",
    assessment_downloads: {
      skillspector: "downloads/assessments/example/skillspector.json",
      adjudication: "downloads/assessments/example/adjudication.json",
    },
    recommendation: "SAFE", risk: "LOW", confidence_flags: [], tags: [],
    scanner_runs: [{ id: "example-run", skill_id: "example", scanner_name: "skillspector", scanner_version: "2", scan_mode: "llm-assisted", last_scanned: timestamp }],
    scanner_findings: [],
    scanner_artifacts: [{ scanner_run_id: "example-run", artifact_kind: "native_report", download_path: "downloads/assessments/example/skillspector.json" }],
    adjudication: {
      status: "completed", summary: "Fixture adjudication summary. <script>alert(1)</script> [untrusted](https://untrusted.example/)",
      coverage_sufficient: true, coverage_reason: "Skill package reviewed", scope: "external references were not assessed",
    },
    dispositions: { true_positive: 1, uncertain: 2, false_positive: 3 },
  };
  write("index.json", JSON.stringify({ skills: [example, {
    ...example, skill_id: "review", name: "Review code",
    description: "Find defects in Python code", scanner_runs: [], scanner_artifacts: [],
  }] }));
  write("assessments/example/skillspector.json", "{}\n");
  write("assessments/example/adjudication.json", "{}\n");
  // An empty, valid ZIP: this test checks serving, not skill-package contents.
  write("zips/example.zip", Buffer.from("504b0506000000000000000000000000000000000000", "hex"));
}
