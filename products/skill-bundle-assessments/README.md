# Read the bundle's assessment results

This download contains assessment reports for the supplied skills. Use it to understand confirmed problems, findings that still need investigation, false positives, and review limitations before deciding how to use a skill.

It contains evidence, not the skill packages themselves. Obtain the matching `skill-bundle-<version>.zip` if you also want to install the skills. Choose both downloads from the same [SkLC release](https://github.com/Code-dot-mil/SkLC/releases) and compare their SHA-256 checksums with the release-page values before unpacking.

On Linux, use `sha256sum 'skill-bundle-assessments-<version>.zip'`; on macOS, use `shasum -a 256` with that filename. PowerShell provides `Get-FileHash -Algorithm SHA256`. Replace `<version>` with the downloaded version and compare the hexadecimal result with GitHub's value, ignoring the `sha256:` prefix.

After the checksum comparison succeeds, extract the archive, replacing `<version>`:

```sh
unzip 'skill-bundle-assessments-<version>.zip' -d bundle-assessments
```

## Find the report pair

Each skill has its own directory:

```text
<skill-name>/
  skillspector.json
  adjudication.json
```

`skillspector.json` contains the scanner's findings and execution/coverage information. `adjudication.json` reviews those findings in context and records the review's status, scope, judgments, limitations, and skill-content hash. Keep both JSON files together; they describe the exact skill contents assessed, rather than every later revision of that skill.

## Produce a readable summary

Install the assessment-kit wheel by following its [installation guide](https://github.com/Code-dot-mil/SkLC/blob/main/products/assessment-kit/README.md#installation). Reading existing reports requires Python and the installed kit, but no SkillSpector installation, provider credentials, or new scan.

From the working directory containing the installation's `.venv`, point `--assessment-dir` at the selected skill's extracted directory. For example, if you extracted this download into `bundle-assessments/` there:

```sh
uv run --no-project skill-assessment summarize   --assessment-dir ./bundle-assessments/python-secure-code-review > assessment.md
```

Open `assessment.md`. The command reads the reports without changing them. See [summary interpretation](https://github.com/Code-dot-mil/SkLC/blob/main/products/assessment-kit/README.md#summarize) for detailed usage.

## Decide what needs attention

| Summary result | Next action |
| --- | --- |
| Confirmed finding / true positive | Inspect the reason and remediation guidance before using the affected behavior. |
| Unresolved finding | Investigate; uncertainty or incomplete adjudication remains. |
| False positive | Read the contextual reason why this finding requires no remediation. |
| Coverage limitation | Check what was missed and whether it affects your intended use. |

Read the scope and coverage even when the confirmed-finding count is zero. Adjudication examines `SKILL.md` and scanner evidence; it does not independently review supporting files. A successful scan or `safe_to_use: true` is not certification of the whole package.

Summarizing checks that findings and determinations agree, but does not compare the reports with your local skill files. If you modify a skill, assess that version again using the [assessment guide](https://github.com/Code-dot-mil/SkLC/blob/main/products/assessment-kit/README.md#assess).

## How these reports are maintained

In the source repository, the main assessment workflow maintains current successful pairs under `products/skill-bundle-assessments/`, reusing matching results when eligible. Git retains earlier committed versions. Reports for removed or renamed skills are pruned after successful assessment.

`scanner.log` is troubleshooting output rather than part of this download. Failed runs retain diagnostics as job artifacts and do not commit failed results. The downloaded JSON pairs are retained unchanged.
