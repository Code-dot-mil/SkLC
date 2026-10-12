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

## 4. SkillSpector

NVIDIA SkillSpector will be the baseline skill assessor in `llm-assisted` scan mode.
`static-only` has a high false positive rate, must be explicitly requested, and must
not be used as a fallback when `llm-assisted` is configured but unavailable.

SkillSpector installation and dependency management are outside this repository's
scope. The assessment kit requires an externally installed `skillspector` executable
on `PATH` for advice and assessment; validation has no scanner prerequisite.
The compatibility target is SkillSpector `>=2.10,<3` through its public CLI and JSON report format.
Version 2.10.0 is tested; later v2 releases are expected to remain compatible.

## 5. Assessment errors

Define all assessment-kit exception types in `skill_assessment/errors.py`. Commands and callers import these shared types; command modules own parsing and execution, not exception definitions.

## 6. Assessment distribution

Publish the existing assessment-kit wheel directly on authorized SkLC releases,
as the third product alongside the deployment and catalog ZIPs, using GitHub
asset digests for download integrity. Its package version must correspond
to the release version under Python packaging normalization. Before upload, prove
all three commands work outside the checkout with the installed wheel and supported
SkillSpector; explicit static scanning is sufficient for this installation proof.
