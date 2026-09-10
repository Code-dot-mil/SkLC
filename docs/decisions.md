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

NVIDIA SkillSpector will be the baseline skill assessor in `llm-assisted` scan mode. `static-only` has a high false positive rate, must be explicitly requested, and must not be used as a fallback when `llm-assisted` is configured but unavailable.

The first assessment-kit release supports the `openai_compatible` SkillSpector
provider profile through generic `SKLC_LLM_*` inputs and records one exact
tested SkillSpector version or source revision. Additional provider profiles or
assessor versions require explicit documentation and compatibility tests.
