# Requirements

## 1. Customer environment

The primary environment that customer requires us to support for hostable products is GitLab.

## 2. Maintainer environment

The environment that maintainers must use as source of truth and produce releases from is a private GitHub repository, except skill lifecycle guidance, which will be published from the Code-dot-mil AI4SDLC GitHub.

## 3. Products

The team shall deliver 4 standalone products:

- Skill lifecycle (SkLC) guidance and documentation
- Initial skill catalog for a developer persona with 4 skills
- Assessment kit
- Deployment kit

Lifecycle guidance is a parallel, non-gating track published from the Code-dot-mil AI4SDLC GitHub. Its minimum useful customer-facing shape remains to be accepted. The current direction uses Define, Build, Validate, Release, and Operate stages, with user, author, reviewer, and operator roles. Catalog approval authority is recorded at Release rather than introduced as a standing lifecycle role.

## 4. SkillSpector

NVIDIA SkillSpector will be the baseline skill assessor in `llm-assisted` scan mode. `static-only` has a high false positive rate, must be explicitly requested, and must not be used as a fallback when `llm-assisted` is configured but unavailable.

SkillSpector installation and dependency management are outside the assessment kit's scope. Upstream assessment CI installs its pinned scanner at runtime; consumers provide their own installation. The assessment kit requires an external `skillspector` executable on `PATH` for assessment; validation, hashing, and summaries need no scanner. The compatibility target is SkillSpector `>=2.10,<3` through its public CLI and JSON report format. Versions 2.10.0 and 2.12.0 have been exercised; other v2 releases are expected to remain compatible.

## 5. Assessment errors

Define all assessment-kit exception types in `skill_assessment/errors.py`. Commands and callers import these shared types; command modules own parsing and execution, not exception definitions.

## 6. Assessment distribution

Publish the assessment-kit wheel independently on authorized SkLC releases alongside the ZIP downloads listed in [CI](../CI.md#prepare-a-draft), using GitHub asset digests for download integrity. All artifacts share one release version; components are not independently versioned. The wheel's package version must correspond to that release version under Python packaging normalization. Use `uv build` to build the wheel and rely on the Python packaging tools for wheel validation.

## 7. Coverage and current assessment scope

The current catalog skills each contain only SKILL.md and no supporting files. Coverage diagnostics do not determine the safety verdict; safety is judged from SKILL.md content and adjudicated findings. Preserve native coverage diagnostics as information. Reliable coverage assessment for arbitrary multi-file skill packages is deferred to future work. This decision requires no changes to SkillSpector.

## 8. Catalog safety gate

PR CI and release CI require every catalog skill to have a Safe to use determination after validating current assessments against exact skill content. Missing, unknown, or unfavorable determinations fail the gate before packaging and draft release creation. Coverage diagnostics do not affect this gate. Operator sites may still display unfavorable assessments.
