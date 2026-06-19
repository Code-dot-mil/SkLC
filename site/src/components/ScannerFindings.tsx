import { useMemo, useRef, useState } from "react";

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
};

type Artifact = {
  scanner_run_id: string;
  artifact_kind: string;
  download_path: string;
};

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
  const [selectedRunId, setSelectedRunId] = useState(defaultRun?.id || "");
  const [severity, setSeverity] = useState("all");
  const selectedRun = sortedRuns.find((run) => run.id === selectedRunId) || sortedRuns[0];
  const severities = useMemo(
    () =>
      Array.from(
        new Set(
          scannerFindings
            .filter((finding) => finding.scanner_run_id === selectedRun?.id)
            .map((finding) => finding.severity)
            .filter(Boolean)
        )
      ).sort(),
    [scannerFindings, selectedRun?.id]
  );
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
            <button className="dialog-close" aria-label="Close">Close</button>
          </form>
          <h2>Scanner Runs</h2>
          <p>
            Each run records the output from SkillSpector, a third-party external scanner from NVIDIA.
            Static-only mode skips LLM review and is faster but lower confidence. LLM-assisted mode adds semantic review when configured.
          </p>
          <p>
            More details about findings and methodology are available on the{" "}
            <a href="https://github.com/NVIDIA/SkillSpector">NVIDIA SkillSpector GitHub page</a>.
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
              <th>Download Results</th>
            </tr>
          </thead>
          <tbody>
            {sortedRuns.map((run) => {
              const nativeReport = scannerArtifacts.find(
                (artifact) => artifact.scanner_run_id === run.id && artifact.artifact_kind === "native_report"
              );
              const findingCount = scannerFindings.filter((finding) => finding.scanner_run_id === run.id).length;
              const selected = run.id === selectedRun.id;
              return (
                <tr
                  className={selected ? "selected-row" : ""}
                  key={run.id}
                  tabIndex={0}
                  onClick={() => {
                    setSelectedRunId(run.id);
                    setSeverity("all");
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      setSelectedRunId(run.id);
                      setSeverity("all");
                    }
                  }}
                >
                  <td>{run.scanner_name} {run.scanner_version}</td>
                  <td>{formatDate(run.last_scanned)}</td>
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
                          onClick={(event) => {
                            event.stopPropagation();
                            navigator.clipboard?.writeText(run.content_hash || "");
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
      </section>

      <section className="card">
        <div className="section-title-row">
          <h2>Findings</h2>
          <ModePill run={selectedRun} />
        </div>
        <p>
          <strong>Selected Run Risk Level:</strong>{" "}
          <RiskPills risk={selectedRun.display_risk || "Unknown"} flags={selectedRun.confidence_flags || []} />
        </p>
        <div className="controls">
          <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="all">All risk levels</option>
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
                    <span className={`risk risk-${String(finding.severity || "unknown").toLowerCase()}`}>
                      {finding.severity || "Unknown"}
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

function formatDate(value?: string) {
  if (!value) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
