# August 2026 Task Roadmap

## Goal

Make GitHub the authoritative source and publication system for the Skill Exchange, establish a permanent internal runner for trusted assessments, and deliver two supported downstream deployment packages:

1. A static-site package for organizations that only need to host the exchange as delivered.
2. An operator package for organizations that need to add skills, run assessments, exclude delivered skills, and deploy a customized exchange.

This work stays in one repository. It does not require splitting the project into separate repositories.

## Terms

| Term | Meaning |
|---|---|
| **Body of Evidence (BOE)** | Durable assessment evidence for a skill, including scanner output, assessment result, provenance, configuration, and integrity data. |
| **GitHub Actions** | GitHub's continuous-integration system. |
| **Self-hosted GitHub Actions runner** | MITRE-operated compute that executes selected GitHub Actions jobs. This is the GitHub equivalent of a GitLab Runner. |
| **Ephemeral runner pod** | A Kubernetes pod that executes a CI job and is then discarded. |
| **Trusted assessment job** | A GitHub Actions job authorized to call internal services and create or reuse BOE. |
| **M-DEVCHAT** | MITRE's Level 1, non-CUI LLM service used for LLM-assisted skill evaluation and code review. |
| **Static-site package** | A release package containing an already-built exchange site. It cannot add skills or run assessments. |
| **Operator package** | A release package containing the exchange tooling, delivered skills and BOE, and a supported local customization area. |
| **Catalog builder** | The build component that converts skills, BOE, and policy into indexes, detail data, tables, and downloads. |
| **Astro builder** | The static-site build step that converts catalog artifacts into the final website. |
| **Local overlay** | Consumer-owned content under `local/` that upstream updates never overwrite. |

## Scope

Included in this roadmap:

- GitHub as the authoritative source repository.
- GitHub Actions workflows and GitHub Pages deployment.
- A permanent CMMC Level 1 EPIC environment for the trusted self-hosted runner.
- Temporary use of the existing AI Platform Level 2 Kubernetes namespace only while the permanent EPIC runner is being established.
- Static-site and operator release packages.
- Generic static-host and GitLab Pages deployment options.
- Local skill, local BOE, and local exclusion support for operator deployments.

Not included:

- Arbitrary custom UI support.
- Assessment-only packaging for organizations building an entirely separate exchange.
- Repository splitting.

## Staffing

| Role | Availability | Primary responsibility |
|---|---:|---|
| L3 engineer | 50% | Permanent runner environment, temporary bridge, architecture/data-flow documentation, and integration decisions. |
| L1 engineer | 50% | GitHub migration, release packaging, downstream deployment paths, and implementation. |
| Intern | 10% | Documentation, customer deployment walkthroughs, release checklists, and consumer smoke-test fixtures. |

## Workstream 1: Permanent trusted assessment runner

### Objective

Establish the long-term home for trusted GitHub Actions assessment work in a CMMC Level 1 EPIC environment.

### L3 tasks

1. Request and pursue the permanent runner environment immediately:
   - Preferred option: an EPIC Level 1 virtual machine.
   - Alternative option: an EPIC Level 1 Kubernetes namespace, if available and appropriate.
   - Select the approved long-term option and document the decision.

2. Deliver the permanent self-hosted GitHub Actions runner in that environment.

3. Define the runner's narrow operational purpose:
   - receive non-CUI CI work from a MITRE-controlled GitHub repository;
   - send non-CUI evaluation requests to M-DEVCHAT;
   - return non-CUI review comments, BOE, and build artifacts to GitHub.

4. Produce the architecture diagram and narrative required for the temporary AI Platform deployment and the permanent EPIC deployment. The AI Platform CMMC description must cover only the internal boundary:
   - no interactive user access;
   - no user-facing ingress or exposed application/service port;
   - non-CUI GitHub repository content and jobs as inputs;
   - non-CUI requests and responses to and from M-DEVCHAT;
   - non-CUI comments and artifacts returned to GitHub;
   - no CUI received, stored, processed, or transmitted.

5. Deploy the temporary ephemeral runner pod in the existing AI Platform Level 2 Kubernetes namespace only to validate the GitHub integration while the EPIC environment is obtained.

6. Define and execute the migration from the temporary AI Platform runner to the permanent EPIC runner. Retire the temporary runner from normal operation after the EPIC runner is proven.

### L1 tasks

1. Define the GitHub Actions job that targets the self-hosted runner for trusted assessment.
2. Work with L3 to validate that the temporary runner pod can execute the job and return its results to GitHub.
3. Move the job target to the permanent EPIC runner when L3 completes the environment delivery.

### Intern tasks

1. Assist with the architecture diagram, terminology, and data-flow narrative.
2. Maintain a CI behavior matrix: job name, triggering event, runner type, input, output, and purpose.

### Completion criteria

- The permanent EPIC Level 1 runner executes trusted assessment jobs from GitHub.
- The temporary AI Platform runner is no longer required for ordinary operation.
- The temporary and permanent environment diagrams and narratives are complete.

## Workstream 2: GitHub source and reference exchange publication

### Objective

Make GitHub the authoritative source repository and publish the reference static exchange through GitHub Pages.

### L1 tasks

1. Create GitHub Actions workflows for ordinary checks, trusted assessment, catalog materialization, Astro build, release assembly, and GitHub Pages deployment.
2. Route ordinary validation and test jobs to GitHub-hosted runners.
3. Route trusted assessment jobs to the self-hosted runner.
4. Preserve the existing behavior for skill assessment, BOE reuse or creation, catalog artifact generation, and Astro static-site generation.
5. Produce versioned release metadata containing source revision, release version, artifact checksums, and BOE/catalog provenance.

### L3 tasks

1. Review the handoff between GitHub-hosted jobs and trusted-runner jobs.
2. Confirm that the permanent runner supports the trusted assessment workflow.

### Intern tasks

1. Update contributor and publication documentation.
2. Maintain the release acceptance checklist.

### Completion criteria

- A protected default-branch change can create or reuse BOE, materialize catalog artifacts, build the Astro site, and deploy GitHub Pages.
- A release produces traceable version and checksum metadata.

## Workstream 3: Static-site package for minimally technical consumers

### Objective

Deliver a package for an organization that wants to host the exchange exactly as released, without running assessments, adding skills, or operating build tooling.

### Package contents

- Final static site files and downloads.
- Release manifest and checksums.
- Generic static-host deployment instructions.
- A minimal GitLab Pages deployment wrapper that publishes supplied static content only.

The package must not contain scanner tooling, LLM configuration, local customization capability, or source build dependencies.

### L1 tasks

1. Add release assembly for the static-site package.
2. Produce a generic static-host archive.
3. Produce a minimal GitLab Pages deployment wrapper.
4. Verify that the package contains only the files needed to host the static exchange.

### L3 tasks

1. Review package provenance and verification requirements.
2. Review the static package boundary before release.

### Intern tasks

1. Write the customer deployment walkthrough:
   - download the GitHub release;
   - verify manifest and checksums;
   - deploy to a generic static host or GitLab Pages;
   - apply a future update by replacing the delivered static package.
2. Maintain a smoke test that verifies expected site files and downloads are present and assessment tooling is absent.

### Completion criteria

A minimally technical organization can manually receive a GitHub release and host the unchanged exchange through generic static hosting or GitLab Pages.

## Workstream 4: Operator package for local skills and assessments

### Objective

Deliver a package for an organization that needs to add local skills, create local BOE, exclude selected delivered skills, and deploy its own exchange.

### Operator package layout

```text
app/                    Delivered application and build tooling
skills/                 Delivered skill packages
boe/                    Delivered accepted Body of Evidence bundles
site/                   Delivered reference site source

local/
  skills/               Consumer-added skill packages
  boe/                  Body of Evidence for consumer-added skills
  catalog.yaml          Consumer catalog preferences and exclusions
```

Upstream updates replace the delivered directories and preserve `local/`.

### L3 tasks

1. Define and approve the ownership and update contract.
2. Define the policy boundary for exclusions expressed through `local/catalog.yaml`.
3. Define when local skills are assessed on a developer workstation and when they are assessed through a trusted GitLab runner.
4. Review update safety: manifest verification, staged replacement of delivered content, preservation of `local/`, and recording of the applied release version.

### L1 tasks

1. Build the operator package and update mechanism.
2. Implement support for `local/skills/`, `local/boe/`, and `local/catalog.yaml`.
3. Ensure exclusions remove a skill from all served outputs: index/search data, detail records, downloads, tables, and generated routes.
4. Provide GitLab CI configuration for trusted local-skill assessment, catalog build, Astro build, GitLab Pages deployment, and generic static-host artifacts.
5. Provide supported local commands for assessment and build outside GitLab CI.

### Intern tasks

1. Write and validate the operator walkthrough:
   - install the operator package;
   - add a skill under `local/skills/`;
   - run assessment locally or through GitLab CI;
   - exclude a delivered skill through `local/catalog.yaml`;
   - apply a later upstream release;
   - verify local skills, local BOE, and catalog preferences remain intact.
2. Maintain a consumer smoke-test fixture proving that workflow.

### Completion criteria

An organization can receive an upstream operator release, preserve local additions and preferences, assess local skills, exclude selected delivered skills, and deploy its customized exchange through GitLab Pages or another static host.

## Delivery sequence

1. Start the EPIC Level 1 runner request and temporary AI Platform runner work immediately.
2. In parallel, move source and reference publication to GitHub and deploy GitHub Pages.
3. Deliver the static-site package and validate the customer deployment walkthrough.
4. Deliver the operator package and validate it through the internal GitLab consumer deployment.

The operator package must reuse the same release manifest and verification mechanism established for the static-site package. It must not introduce a separate update system.
