import { useEffect, useMemo, useRef } from "react";

import { readQueryValue, replaceQueryState } from "../lib/url-state.mjs";
import { useQueryString } from "../lib/use-query-string";

export type ScannerRun = {
  id: string;
  scanner_name: string;
  scanner_version: string;
  scan_mode: string;
  native_score?: number;
  native_severity?: string;
  last_scanned?: string;
  llm_provider?: string;
  llm_model?: string;
  display_risk?: string;
  confidence_flags?: string[];
  content_hash?: string;
};

export type Finding = {
  id: string;
  scanner_run_id: string;
  native_issue_id: string;
  severity?: string;
  category?: string;
  pattern?: string;
  path?: string;
  start_line?: number;
  explanation?: string;
  remediation?: string;
  code_snippet?: string;
  determination: "true_positive" | "uncertain" | "false_positive";
  adjudication_reason: string;
};

export type Artifact = {
  scanner_run_id: string;
  artifact_kind: string;
  download_path: string;
};

const outcomes = {
  true_positive: { label: "Confirmed issue", priority: 0 },
  uncertain: { label: "Unresolved: human review needed", priority: 1 },
  false_positive: { label: "Adjudicated as false positive", priority: 2 },
};

export default function ScannerFindings({
  currentRun,
  scannerFindings,
}: {
  currentRun?: ScannerRun;
  scannerFindings: Finding[];
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const search = useQueryString();
  const severities = useMemo(
    () =>
      Array.from(
        new Set(
          scannerFindings
            .filter((finding) => finding.scanner_run_id === currentRun?.id)
            .map((finding) => finding.severity)
            .filter((severity): severity is string => Boolean(severity))
        )
      ).sort((left, right) => {
        if (left === right) return 0;
        return left < right ? -1 : 1;
      }),
    [scannerFindings, currentRun?.id]
  );
  const severity = readQueryValue(search, "severity", "all", ["all", ...severities]);
  useEffect(() => {
    if (!currentRun) return;
    const params = new URLSearchParams(search);
    if (params.has("run") || params.has("runs") || (params.has("severity") && params.get("severity") !== severity)) {
      replaceQueryState({ run: null, runs: null, severity }, { severity: "all" });
    }
  }, [currentRun, search, severity]);

  const currentFindings = scannerFindings.filter((finding) => finding.scanner_run_id === currentRun?.id);
  for (const finding of currentFindings) {
    if (!Object.hasOwn(outcomes, finding.determination)) {
      throw new Error("Finding determination is missing or invalid. Regenerate the site data from current assessments.");
    }
  }
  const visibleFindings = currentFindings
    .filter((finding) => severity === "all" || finding.severity === severity)
    .sort((left, right) => outcomes[left.determination].priority - outcomes[right.determination].priority);


  if (!currentRun) {
    return (
      <section className="card">
        <h2>Scanner findings</h2>
        <p>No current assessment is available.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="section-title-row">
        <h2>Scanner findings</h2>
        <button className="icon-button" type="button" onClick={() => dialogRef.current?.showModal()} aria-label="About scanner findings">i</button>
      </div>
      <dialog ref={dialogRef}>
        <form method="dialog">
          <button className="dialog-close" type="submit" aria-label="Close">Close</button>
        </form>
        <h2>Scanner findings</h2>
        <p>SkillSpector reports possible problems. A separate AI review checks those findings.</p>
        <p>A warning marked <strong>Adjudicated as false positive</strong> was judged to be a false alarm by that review.</p>
        <p>The scanner risk can differ from the recommendation. The recommendation reflects adjudication.</p>
        <a className="external-link" href="https://github.com/NVIDIA/SkillSpector" target="_blank" rel="noreferrer" referrerPolicy="no-referrer">NVIDIA SkillSpector</a>
      </dialog>
      <p className="muted">Original scanner warnings are shown below with their AI review outcomes.</p>
      <div className="controls">
        <select aria-label="Finding severity" value={severity} onChange={(event) => replaceQueryState({ run: null, runs: null, severity: event.target.value }, { severity: "all" })}>
          <option value="all">All finding severities</option>
          {severities.map((item) => (
            <option value={item} key={item}>
              {item}
            </option>
          ))}
        </select>
      </div>
      {visibleFindings.length === 0 ? (
        <p>No findings match the current assessment and severity filter.</p>
      ) : (
        <div className="finding-list">
          {visibleFindings.map((finding) => {
            const location = finding.path ? `${finding.path}:${finding.start_line || "?"}` : "Unknown";
            return (
              <article className={`finding-card finding-${finding.determination}`} key={finding.id}>
                <header className="finding-card-header">
                  <div>
                    <strong>{finding.native_issue_id}</strong>
                    <span className="muted"> {finding.category || "Uncategorized"}</span>
                  </div>
                  <span className="pill-row">
                    <span className={`risk flag outcome-${finding.determination}`}>{outcomes[finding.determination].label}</span>
                    <span className="muted">Scanner: {finding.severity || "Unknown"}</span>
                  </span>
                </header>
                <details className="assessment-advanced" open={finding.determination !== "false_positive"}>
                  <summary>View finding details</summary>
                  <p><strong>AI review:</strong> {finding.adjudication_reason}</p>
                  <p><strong>{finding.pattern || "Finding"}</strong></p>
                  <p><strong>Scanner explanation:</strong> {finding.explanation || "No explanation provided."}</p>
                  <p><strong>Location:</strong> <code>{location}</code></p>
                  {finding.code_snippet && <pre><code>{finding.code_snippet}</code></pre>}
                  <p><strong>Scanner remediation:</strong> {finding.remediation || "No remediation provided."}</p>
                </details>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
