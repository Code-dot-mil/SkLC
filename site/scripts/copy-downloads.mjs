import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, rmSync } from "node:fs";
import { dirname, isAbsolute, join, resolve, sep } from "node:path";

const siteRoot = process.cwd();
const repositoryRoot = resolve(siteRoot, "..");
const target = resolve(siteRoot, "public", "downloads");
const generatedRoot = resolve(repositoryRoot, ".exchange", "generated");
const scannerRunsRoot = resolve(generatedRoot, "scanner-runs");
const zipSource = resolve(generatedRoot, "zips");
const artifactsTable = resolve(generatedRoot, "tables", "scanner_artifacts.json");

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
    const source = resolveArtifactSource(artifact.path);
    const destination = resolveDownloadDestination(artifact.download_path);
    if (existsSync(source)) {
      mkdirSync(dirname(destination), { recursive: true });
      cpSync(source, destination);
    }
  }
}

function resolveArtifactSource(pathValue) {
  const source = isAbsolute(pathValue)
    ? rebaseGeneratedScannerPath(pathValue)
    : resolve(repositoryRoot, pathValue);
  assertInside(source, scannerRunsRoot, "artifact source is outside .exchange/generated/scanner-runs");
  if (existsSync(source) && existsSync(scannerRunsRoot)) {
    const realSource = realpathSync(source);
    const realScannerRunsRoot = realpathSync(scannerRunsRoot);
    assertInside(realSource, realScannerRunsRoot, "artifact source is outside .exchange/generated/scanner-runs");
  }
  return source;
}

function rebaseGeneratedScannerPath(pathValue) {
  const source = resolve(pathValue);
  const marker = `${sep}.exchange${sep}generated${sep}scanner-runs${sep}`;
  const markerIndex = source.indexOf(marker);
  if (markerIndex === -1) {
    return source;
  }
  return resolve(scannerRunsRoot, source.slice(markerIndex + marker.length));
}

function resolveDownloadDestination(downloadPath) {
  const relative = String(downloadPath).replace(/^\/+/, "");
  const destination = resolve(siteRoot, "public", relative);
  assertInside(destination, target, "artifact destination is outside public/downloads");
  return destination;
}

function assertInside(child, parent, message) {
  const normalizedChild = resolve(child);
  const normalizedParent = resolve(parent);
  if (normalizedChild !== normalizedParent && !normalizedChild.startsWith(normalizedParent + sep)) {
    throw new Error(`${message}: ${child}`);
  }
}
