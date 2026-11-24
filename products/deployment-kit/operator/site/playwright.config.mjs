import { basename, dirname, resolve } from "node:path";
import { defineConfig } from "@playwright/test";

if (!process.env.SKLC_SITE_DIR || !process.env.SKLC_SITE_REVISION) {
  throw new Error("Set SKLC_SITE_DIR to the staged public directory and SKLC_SITE_REVISION to its source commit.");
}
const site = resolve(process.env.SKLC_SITE_DIR);
if (basename(site) !== "public") throw new Error("Expected the Prebuilt artifact's public directory.");

const mounts = [
  { name: "root", cwd: site, port: 4173, path: "/" },
  { name: "nested", cwd: dirname(site), port: 4174, path: "/public/" },
];
const url = mount => `http://127.0.0.1:${mount.port}${mount.path}`;

export default defineConfig({
  testDir: "./tests/e2e",
  workers: 1,
  globalTimeout: 180_000,
  use: { trace: "retain-on-failure" },
  projects: mounts.map(mount => ({ name: mount.name, use: { baseURL: url(mount) } })),
  webServer: mounts.map(mount => ({
    command: `python -m http.server ${mount.port} --bind 127.0.0.1`,
    cwd: mount.cwd,
    url: url(mount) + "index.html",
  })),
});
