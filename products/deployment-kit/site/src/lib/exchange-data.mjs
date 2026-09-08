import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const repositoryRoot = process.env.SKILL_EXCHANGE_REPOSITORY_ROOT || resolve(process.cwd(), "../../..");
const generatedRoot = process.env.SKILL_EXCHANGE_GENERATED_ROOT
  || resolve(repositoryRoot, "maintainer", "exchange", "generated");

export const exchangeIndex = readGeneratedJson("index.json", { skills: [] });
export const scannerRunsTable = readGeneratedJson("tables/scanner_runs.json", { rows: [] });
export const scannerFindingsTable = readGeneratedJson("tables/scanner_findings.json", { rows: [] });
export const scannerArtifactsTable = readGeneratedJson("tables/scanner_artifacts.json", { rows: [] });

function readGeneratedJson(relativePath, fallback) {
  const path = resolve(generatedRoot, relativePath);
  if (!existsSync(path)) {
    return fallback;
  }
  return JSON.parse(readFileSync(path, "utf-8"));
}
