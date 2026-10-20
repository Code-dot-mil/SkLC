import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const generatedRoot = process.env.SKILL_EXCHANGE_GENERATED_ROOT;
if (!generatedRoot) throw new Error("Set SKILL_EXCHANGE_GENERATED_ROOT to the generated site data directory.");

export const exchangeIndex = JSON.parse(readFileSync(resolve(generatedRoot, "index.json"), "utf-8"));
export const scannerRunsTable = { rows: exchangeIndex.skills.flatMap((skill) => skill.scanner_runs) };
export const scannerFindingsTable = { rows: exchangeIndex.skills.flatMap((skill) => skill.scanner_findings) };
export const scannerArtifactsTable = { rows: exchangeIndex.skills.flatMap((skill) => skill.scanner_artifacts) };
