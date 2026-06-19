import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";

const target = join("public", "downloads");
const zipSource = join("..", ".exchange", "generated", "zips");
const artifactsTable = join("..", ".exchange", "generated", "tables", "scanner_artifacts.json");

rmSync(target, { force: true, recursive: true });
mkdirSync(target, { recursive: true });

if (existsSync(zipSource)) {
  for (const entry of readdirSync(zipSource)) {
    if (entry.endsWith(".zip")) {
      cpSync(join(zipSource, entry), join(target, entry));
    }
  }
}

if (existsSync(artifactsTable)) {
  const artifacts = JSON.parse(readFileSync(artifactsTable, "utf-8"));
  for (const artifact of artifacts.rows || []) {
    if (!artifact.path || !artifact.download_path) {
      continue;
    }
    const source = join("..", artifact.path);
    const destination = join("public", artifact.download_path.replace(/^\/+/, ""));
    if (existsSync(source)) {
      mkdirSync(dirname(destination), { recursive: true });
      cpSync(source, destination);
    }
  }
}
