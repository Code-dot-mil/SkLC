import { useEffect, useMemo, useRef, useState } from "react";

import { readQueryValue, replaceQueryState } from "../lib/url-state.mjs";
import LocalDate from "./LocalDate";

type ScannerRun = {
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

type Finding = {
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
  false_positive?: boolean;
};

type Artifact = {
  scanner_run_id: string;
  artifact_kind: string;
  download_path: string;
};

const RUNS_VALUES = ["latest", "all"];

export default function ScannerFindings({
  scannerRuns,
  scannerFindings,
  scannerArtifacts,
}: {
  scannerRuns: ScannerRun[];
  scannerFindings: Finding[];
  scannerArtifacts: Artifact[];
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const sortedRuns = useMemo(
    () => [...scannerRuns].sort((left, right) => Date.parse(right.last_scanned || "") - Date.parse(left.last_scanned || "")),
    [scannerRuns]
  );
  const defaultRun = sortedRuns[0];
  const runIds = useMemo(() => sortedRuns.map((run) => run.id), [sortedRuns]);
  const runIdsKey = runIds.join("|");
  const [selectedRunId, setSelectedRunId] = useState(defaultRun?.id || "");
  const [severity, setSeverity] = useState("all");
  const [showOlderRuns, setShowOlderRuns] = useState(false);
  const [queryStateReady, setQueryStateReady] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const selectedRun = sortedRuns.find((run) => run.id === selectedRunId) || sortedRuns[0];
  const displayedRuns = showOlderRuns ? sortedRuns : sortedRuns.slice(0, 1);
  const olderRunCount = Math.max(sortedRuns.length - 1, 0);
  // Keep ordering identical during static rendering and browser hydration.
  const severities = useMemo(
    () =>
      Array.from(
        new Set(
          scannerFindings
            .filter((finding) => finding.scanner_run_id === selectedRun?.id)
            .map((finding) => finding.severity)
            .filter((severity): severity is string => Boolean(severity))
        )
      ).sort((left, right) => {
        if (left === right) return 0;
        return left < right ? -1 : 1;
      }),
    [scannerFindings, selectedRun?.id]
  );
  useEffect(() => {
    const defaultRunId = defaultRun?.id || "";
    const nextRunId = readQueryValue(window.location.search, "run", defaultRunId, runIds);
    const nextRuns = readQueryValue(window.location.search, "runs", "latest", RUNS_VALUES);
    setSelectedRunId(nextRunId);
    setSeverity(
      readQueryValue(window.location.search, "severity", "all", [
        "all",
        ...findingSeveritiesForRun(scannerFindings, nextRunId),
      ])
    );
    setShowOlderRuns(nextRuns === "all" || Boolean(nextRunId && nextRunId !== defaultRunId));
    setQueryStateReady(true);
  }, [defaultRun?.id, runIds, runIdsKey, scannerFindings]);

  useEffect(() => {
    if (severity !== "all" && !severities.includes(severity)) {
      setSeverity("all");
    }
  }, [severity, severities]);

  useEffect(() => {
    if (!queryStateReady || !selectedRun) {
      return;
    }
    replaceQueryState(
      { run: selectedRun.id, runs: showOlderRuns ? "all" : "latest", severity },
      { run: defaultRun?.id || "", runs: "latest", severity: "all" }
    );
  }, [defaultRun?.id, queryStateReady, selectedRun, severity, showOlderRuns]);

  const visibleFindings = scannerFindings.filter((finding) => {
    if (finding.scanner_run_id !== selectedRun?.id) {
      return false;
    }
    return severity === "all" || finding.severity === severity;
  });

  if (!selectedRun) {
    return (
      <section className="card">
        <h2>Scanner Runs</h2>
        <p>No scanner runs are available.</p>
      </section>
    );
  }

  return (
    <>
      <section className="card">
        <div className="section-title-row">
          <div className="title-cluster">
            <h2>Scanner Runs</h2>
            <button className="icon-button" type="button" onClick={() => dialogRef.current?.showModal()} aria-label="About scanner runs">
              i
            </button>
          </div>
        </div>
        <dialog ref={dialogRef}>
          <form method="dialog">
            <button className="dialog-close" type="submit" aria-label="Close">Close</button>
          </form>
          <h2>Scanner Runs</h2>
          <p>This table shows results from SkillSpector, a security scanner from NVIDIA.</p>
          <p>It has two modes:</p>
          <ul>
            <li><strong>Static-only:</strong> A faster scan that skips the scanner’s AI checks.</li>
            <li><strong>LLM-assisted:</strong> Uses AI to help understand what the skill does and look for problems.</li>
          </ul>
          <p>
            SkillSpector uses tags to describe its findings, but those tags don’t clearly identify false positives:
            warnings that aren’t real problems. We use a second AI assistant to review the findings.
            When it decides a warning is a false alarm, we add an <strong>Adjudicated as False Positive</strong> tag beside it.
          </p>
          <p>
            Learn more on the{" "}
            <a className="external-link" href="https://github.com/NVIDIA/SkillSpector" target="_blank" rel="noreferrer" referrerPolicy="no-referrer">
              NVIDIA SkillSpector GitHub page <span aria-hidden="true">↗</span>
            </a>.
          </p>
        </dialog>
        <table>
          <thead>
            <tr>
              <th>Scanner</th>
              <th>Date</th>
              <th>Mode</th>
              <th>Content Hash</th>
              <th>Severity</th>
              <th>Score</th>
              <th>Risk</th>
              <th>Findings</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {displayedRuns.map((run) => {
              const nativeReport = scannerArtifacts.find(
                (artifact) => artifact.scanner_run_id === run.id && artifact.artifact_kind === "native_report"
              );
              const findingCount = scannerFindings.filter((finding) => finding.scanner_run_id === run.id).length;
              const selected = run.id === selectedRun.id;
              return (
                <tr className={selected ? "selected-row" : ""} key={run.id}>
                  <td>
                    <button
                      className="row-select"
                      type="button"
                      aria-pressed={selected}
                      onClick={() => {
                        setSelectedRunId(run.id);
                        setSeverity("all");
                      }}
                    >
                      {selected ? "Selected" : "Select"}
                    </button>{" "}
                    {run.scanner_name} {run.scanner_version}
                  </td>
                  <td><LocalDate value={run.last_scanned} /></td>
                  <td><ModePill run={run} /></td>
                  <td>
                    <span className="hash-cell">
                      <abbr title={run.content_hash}><code>{run.content_hash?.slice(0, 12)}</code></abbr>
                      {run.content_hash && (
                        <button
                          className="icon-button compact"
                          type="button"
                          title="Copy content hash"
                          aria-label="Copy content hash"
                          onClick={async (event) => {
                            event.stopPropagation();
                            setCopyError(false);
                            try {
                              await navigator.clipboard.writeText(run.content_hash || "");
                            } catch {
                              setCopyError(true);
                            }
                          }}
                        >
                          copy
                        </button>
                      )}
                    </span>
                  </td>
                  <td>{run.native_severity || "Unknown"}</td>
                  <td>{run.native_score ?? "n/a"}</td>
                  <td>{run.display_risk || "Unknown"}</td>
                  <td>{findingCount}</td>
                  <td>
                    {nativeReport && (
                      <a className="icon-link" href={nativeReport.download_path} title="Download scanner output" aria-label={`Download ${run.scan_mode} scanner output`} onClick={(event) => event.stopPropagation()}>
                        <span aria-hidden="true">&#8681;</span>
                      </a>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {copyError && <p role="status">Could not copy the content hash. Check clipboard permissions and try again.</p>}
        {olderRunCount > 0 && (
          <div className="centered-action">
            <button
              className="link-button"
              type="button"
              onClick={() => {
                setShowOlderRuns((current) => {
                  if (current) {
                    setSelectedRunId(sortedRuns[0].id);
                    setSeverity("all");
                  }
                  return !current;
                });
              }}
            >
              {showOlderRuns ? "Hide older scanner runs" : "View older scanner runs"}
            </button>
          </div>
        )}
      </section>

      <section className="card">
        <div className="section-title-row">
          <h2>Findings</h2>
          <ModePill run={selectedRun} />
        </div>
        <p>
          <strong>Scanner risk:</strong>{" "}
          <RiskPills risk={selectedRun.display_risk || "Unknown"} flags={selectedRun.confidence_flags || []} />
        </p>
        <div className="controls">
          <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="all">All finding severities</option>
            {severities.map((item) => (
              <option value={item} key={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        {visibleFindings.length === 0 ? (
          <p>No findings were reported for the selected scan and risk filter.</p>
        ) : (
          <div className="finding-list">
            {visibleFindings.map((finding) => {
              const location = finding.path ? `${finding.path}:${finding.start_line || "?"}` : "Unknown";
              return (
                <article className="finding-card" key={finding.id}>
                  <header className="finding-card-header">
                    <div>
                      <strong>{finding.native_issue_id}</strong>
                      <span className="muted"> {finding.category || "Uncategorized"}</span>
                    </div>
                    <span className="pill-row">
                      <span className={`risk risk-${String(finding.severity || "unknown").toLowerCase()}`}>
                        {finding.severity || "Unknown"}
                      </span>
                      {finding.false_positive && <span className="risk flag">Adjudicated as False Positive</span>}
                    </span>
                  </header>
                  <p><strong>{finding.pattern || "Finding"}</strong></p>
                  <p>{finding.explanation || "No explanation provided."}</p>
                  <p><strong>Location:</strong> <code>{location}</code></p>
                  {finding.code_snippet && <pre><code>{finding.code_snippet}</code></pre>}
                  <p><strong>Remediation:</strong> {finding.remediation || "No remediation provided."}</p>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}

function findingSeveritiesForRun(scannerFindings: Finding[], scannerRunId: string) {
  return Array.from(
    new Set(
      scannerFindings
        .filter((finding) => finding.scanner_run_id === scannerRunId)
        .map((finding) => finding.severity)
        .filter((severity): severity is string => Boolean(severity))
    )
  ).sort((left, right) => {
    if (left === right) return 0;
    return left < right ? -1 : 1;
  });
}

function ModePill({ run }: { run: ScannerRun }) {
  const details =
    run.scan_mode === "llm-assisted"
      ? `LLM-assisted scan. Provider: ${run.llm_provider || "unknown"}. Model: ${run.llm_model || "unknown"}.`
      : "Static-only scan. LLM review was not requested for this run.";
  return (
    <span className="risk flag" title={details}>
      {run.scan_mode}
    </span>
  );
}

function RiskPills({ risk, flags }: { risk: string; flags: string[] }) {
  return (
    <span className="pill-row inline-pills">
      <span className={`risk risk-${risk.toLowerCase()}`}>{risk}</span>
      {flags.map((flag) => (
        <span className="risk flag" key={flag}>
          {flag}
        </span>
      ))}
    </span>
  );
}
